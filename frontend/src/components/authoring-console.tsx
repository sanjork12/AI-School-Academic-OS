"use client";
import { useEffect, useState } from "react";
import "./console.css";
import { SyllabusIngestion } from "./syllabus-ingestion";

const API = "http://127.0.0.1:8765/api";
type Evidence = {id:string;label:string;status:string;details:Record<string,unknown>};
type Source = {id:string;title:string;capability:string;database:string|null;snapshots:string[]};
type Artifact = {id:string;title:string;sha256:string;category:string;historical:boolean};
type Role = {id:string;slot:string;semantic_role:string;title:string;purpose:string;source_type:string;source_refs:string[];validation:string;ai_capability:string;blocks:{id:string;text:string;details:Record<string,unknown>;visibility:string}[]};
type Lesson = {roles:Role[];limitations:string[]};
type Question = {id:string;role:string;text:string;inputs:Record<string,unknown>;solution_id:string|null};
type Solution = {id:string;role:string;item_ref:string;steps:string[];answer:string;details:Record<string,unknown>};
type Run = {id:string;status:string;started_at:string;ended_at:string|null;stages:Evidence[];errors:{code:string;message:string;error_type:string}[];warnings:string[];artifact_ids:string[]};
type Curriculum = {topic_code:string;topic_name:string;tier_source:string;warnings:string[];structure:Evidence;mapped:number;total:number;subtopics:{code:string;name:string;notes:string[];objectives:{code:string;official_text:string;source_id:string;mappings:Record<string,unknown>[]}[]}[]};
type History = {id:string;label:string;milestone:string;role:string;mode:string;model:string;accepted:boolean;evidence:Evidence[];limitations:string[]};
async function api<T>(path:string,options?:RequestInit):Promise<T>{
  const res=await fetch(API+path,options);
  if(!res.ok){const body=await res.json().catch(()=>({detail:"Backend unavailable"}));throw new Error(`${res.status}: ${JSON.stringify(body.detail)}`);}
  return res.json();
}
function Details({value,label="Technical details"}:{value:unknown;label?:string}){return <details><summary>{label}</summary><pre>{JSON.stringify(value,null,2)}</pre></details>;}
function EvidenceList({items}:{items:Evidence[]}){return <>{items.map(e=><section className="evidence-row" key={e.id}><strong>{e.label}</strong><span className={`state state-${e.status}`}>{e.status}</span><Details value={e.details}/></section>)}</>;}

export function AuthoringConsole(){
  const [sources,setSources]=useState<Source[]>([]),[mode,setMode]=useState("standard-deviation");
  const [tree,setTree]=useState<Curriculum[]>([]),[tier,setTier]=useState("Foundation"),[node,setNode]=useState("2.1");
  const [history,setHistory]=useState<History[]>([]),[artifacts,setArtifacts]=useState<Artifact[]>([]);
  const [run,setRun]=useState<Run|null>(null),[lesson,setLesson]=useState<Lesson|null>(null);
  const [questions,setQuestions]=useState<Question[]>([]),[solutions,setSolutions]=useState<Solution[]>([]);
  const [tab,setTab]=useState("Lesson Questions"),[selectedHistory,setSelectedHistory]=useState<History|null>(null);
  const [error,setError]=useState(""),[busy,setBusy]=useState(false),[connected,setConnected]=useState(false);
  const [solutionId,setSolutionId]=useState<string|null>(null);
  useEffect(()=>{let alive=true;Promise.all([api<Source[]>("/sources"),api<Curriculum[]>("/curriculum/topic2"),api<History[]>("/history"),api<Artifact[]>("/artifacts")]).then(([s,t,h,a])=>{if(alive){setSources(s);setTree(t);setHistory(h);setArtifacts(a);setConnected(true);}}).catch(e=>{if(alive)setError(String(e));});return()=>{alive=false;};},[]);
  const active=sources.find(s=>s.id===mode),curriculum=tree.find(t=>t.tier_source===tier),sub=curriculum?.subtopics.find(s=>s.code===node);
  async function assemble(){
    setBusy(true);setError("");setLesson(null);setQuestions([]);setSolutions([]);setSelectedHistory(null);
    try{
      const {token}=await api<{token:string}>("/session");
      let next=await api<Run>("/runs/assemble-standard-lesson",{method:"POST",headers:{"Content-Type":"application/json","X-Console-Token":token},body:JSON.stringify({source:"standard-deviation",topic:"standard-deviation",profile:"standard-lesson"})});setRun(next);
      // Poll actual backend state. This delay never produces a success state.
      while(next.status==="queued"||next.status==="running"){await new Promise(r=>setTimeout(r,350));next=await api<Run>(`/runs/${next.id}`);setRun(next);}
      if(next.status==="succeeded"){
        const [l,q,s,a]=await Promise.all([api<Lesson>(`/runs/${next.id}/lesson`),api<Question[]>(`/runs/${next.id}/questions`),api<Solution[]>(`/runs/${next.id}/solutions`),api<Artifact[]>("/artifacts")]);setLesson(l);setQuestions(q);setSolutions(s);setArtifacts(a);
      }else setError(next.errors.map(e=>e.message).join(" ")||"Run blocked");
    }catch(e){setError(String(e));}finally{setBusy(false);}
  }
  return <main className="console">
    <header className="console-header"><div><p className="eyebrow">AI ACADEMIC OS · INTERNAL / EXPERIMENTAL</p><h1>Academic Authoring Console</h1><p>Deterministic lessons · Read-only academic state · No automatic AI calls</p></div><span className="connection">{connected?"LOCAL API CONNECTED":"CONNECTING TO LOCAL API"}</span></header>
    <SyllabusIngestion/>
    {error&&<section role="alert" className="console-error"><strong>Operation could not complete</strong><p>{error}</p><p>Start the local backend and inspect the stage evidence. No automatic retry or provider fallback.</p></section>}
    <div className="console-grid">
      <aside className="console-panel"><h2>Source & curriculum</h2><label htmlFor="source">Source</label><select id="source" value={mode} onChange={e=>{setMode(e.target.value);setSelectedHistory(null);}}>{sources.map(s=><option key={s.id} value={s.id}>{s.title}</option>)}</select><p className="capability">{active?.capability}</p>
        {mode==="standard-deviation"?<><h3>Standard Deviation</h3><p>9MA0 · A Level Statistics</p><p className="tiny">Database: {active?.database}</p><Details value={active?.snapshots} label="Active snapshot IDs"/><p>Sources are rechecked by the existing product services on every assembly.</p></>:<><label htmlFor="tier">Tier</label><select id="tier" value={tier} onChange={e=>setTier(e.target.value)}><option>Foundation</option><option>Higher</option></select><h3>{curriculum?.topic_code} · {curriculum?.topic_name}</h3><nav aria-label="Subtopics">{curriculum?.subtopics.map(s=><button aria-pressed={node===s.code} key={s.code} onClick={()=>setNode(s.code)}>{s.code} {s.name} ({s.objectives.length})</button>)}</nav><p>{tree.reduce((n,t)=>n+t.mapped,0)} / {tree.reduce((n,t)=>n+t.total,0)} objectives mapped</p><p>Unmapped objectives remain visible.</p></>}
      </aside>
      <section className="console-panel console-content">
        {mode==="standard-deviation"?<><div className="action-row"><div><label htmlFor="profile">Lesson profile</label><select id="profile"><option>Standard Lesson</option></select></div><button className="primary" onClick={assemble} disabled={!connected||busy}>Assemble & Validate</button></div><p role="status" data-testid="run-status">{run?`Run ${run.id} · ${run.status}`:"Ready to assemble existing deterministic content"}</p>{run&&<Details value={{started_at:run.started_at,ended_at:run.ended_at,warnings:run.warnings,errors:run.errors}} label="Run record"/>}
          <h2>Standard Lesson {lesson?`· ${lesson.roles.length} roles`:""}</h2>{!lesson&&<p>Run the existing services to inspect the current lesson. Historical P6 evidence is available below.</p>}
          {lesson?.roles.map(role=><article className="role-card" data-testid="lesson-role" key={role.id}><div className="role-heading"><span>{role.slot}</span><h3>{role.title}</h3><span className="badge">{role.source_type}</span><span className="state state-PASS">{role.validation}</span></div><p>{role.semantic_role} · {role.purpose}</p><p className="tiny">{role.ai_capability}</p>{role.blocks.map(b=><div key={b.id} className="student-block"><small>STUDENT CONTENT</small><p>{b.text}</p>{Object.keys(b.details).length>0&&<Details value={b.details} label="Inputs / supporting content"/>}</div>)}<Details value={{slot_id:role.id,source_refs:role.source_refs}} label="Content source references"/></article>)}
          {lesson&&<Details value={lesson.limitations} label="Lesson limitations"/>}
        </>:<><h2>{sub?.code} · {sub?.name}</h2><button disabled>Generate Lesson</button><p className="warning">Lesson generation is not available for this curriculum topic yet.</p><p>Missing capability: topic-to-learning/pedagogy adapter. This 4MA1 topic is not connected to the 9MA0 Standard Deviation pipeline.</p>{sub?.notes.map((n,i)=><p key={i}>{n}</p>)}{sub?.objectives.map(o=><article className="objective" key={o.source_id}><h3>Objective {o.code}</h3><p>{o.official_text}</p><code>{o.source_id}</code><p>{o.mappings.length?"Promoted canonical mapping available":"UNMAPPED · human review required"}</p>{o.mappings.length>0&&<Details value={o.mappings} label="Canonical mappings"/>}</article>)}</>}
      </section>
      <aside className="console-panel"><h2>Validation & trust</h2>{mode==="topic2"?<>{curriculum&&<EvidenceList items={[curriculum.structure]}/>}<p className="warning">Structure PASS does not mean official syllabus fully verified.</p>{curriculum?.warnings.map((w,i)=><p className="warning" key={i}>{w}</p>)}</>:<><p>Availability, validity, approval and renderer eligibility are separate states.</p>{run?<EvidenceList items={run.stages}/>:<p>NOT_EVALUATED · assemble to read current evidence.</p>}{selectedHistory&&<><h3>HISTORICAL EVIDENCE · {selectedHistory.role}</h3><EvidenceList items={selectedHistory.evidence}/><p>Academic approval: NOT_EVALUATED</p><p>P6 renderer eligibility: BLOCKED</p></>}</>}</aside>
    </div>
    <section className="console-panel console-bottom"><nav className="tabs" aria-label="Output tabs">{["Lesson Questions","Teacher Solutions","Artifacts","Historical Runs","Presentation"].map(t=><button key={t} aria-pressed={tab===t} onClick={()=>{setTab(t);setSolutionId(null);}}>{t}</button>)}</nav>
      {tab==="Lesson Questions"&&<section data-testid="questions"><h2>Lesson Questions</h2><p>Current Standard Deviation run · student-facing questions; no exam generation.</p>{questions.length===0&&<p>Assemble a Standard Lesson to load questions.</p>}{questions.map(q=><article className="question" key={q.id}><h3>{q.role}</h3><p>{q.text}</p><Details value={q.inputs} label="Question inputs"/>{q.solution_id&&<button onClick={()=>{setSolutionId(q.solution_id);setTab("Teacher Solutions");}}>View linked teacher solution</button>}</article>)}</section>}
      {tab==="Teacher Solutions"&&<section data-testid="solutions"><h2>TEACHER ONLY · Solutions</h2><p>Answers are separate from the student question view.</p>{solutions.length===0&&<p>No current lesson solutions.</p>}{solutions.filter(s=>!solutionId||s.id===solutionId).map(s=><article className="teacher-answer" key={s.id}><h3>{s.role} · {s.id}</h3><ol>{s.steps.map((s,i)=><li key={i}>{s}</li>)}</ol><p>Answer: {s.answer}</p><Details value={s.details}/></article>)}{solutionId&&<button onClick={()=>setSolutionId(null)}>Show all teacher solutions</button>}</section>}
      {(tab==="Artifacts"||tab==="Presentation")&&<section><h2>{tab==="Presentation"?"P5 deterministic / validated presentation":"Registered artifacts"}</h2><p>{tab==="Presentation"?"Existing historical P5 artifacts only. P6 candidate rendering is blocked.":"Read-only downloads by registered artifact ID."}</p>{artifacts.filter(a=>tab!=="Presentation"||a.category==="presentation").map(a=><article key={a.id}><a href={`${API}/artifacts/${a.id}`} download>{a.title}</a><small> · {a.historical?"HISTORICAL":"CURRENT RUN"}</small><Details value={{id:a.id,sha256:a.sha256}} label="Artifact identity"/></article>)}</section>}
      {tab==="Historical Runs"&&<section><h2>HISTORICAL EVIDENCE</h2><p>Frozen P6A.5 / P6A.6 / P6A.7b results. No candidate was generated in this session.</p>{history.map(h=><article key={h.id}><h3>{h.milestone} · {h.role} · {h.accepted?"ACCEPTED":"REJECTED"}</h3><p>{h.mode} · Model: {h.model}</p><button onClick={()=>{setSelectedHistory(h);setMode("standard-deviation");}}>Inspect evidence</button><Details value={{id:h.id,evidence:h.evidence,limitations:h.limitations}} label="Historical validation details"/></article>)}</section>}
    </section>
  </main>;
}
