// Mechanical editable-shape backend. Teaching content arrives only in the
// Python resolver's reference-bound plan; this module creates no teaching text.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';

const [planPath,buildDir,finalPath,skillDir,pythonExecutable]=process.argv.slice(2);
if(![planPath,buildDir,finalPath,skillDir,pythonExecutable].every(v=>v&&path.isAbsolute(v)))throw Error('Absolute renderer paths required');
const requireRuntime=createRequire(path.join(process.env.RUNTIME_NODE_MODULES,'__p4c__.cjs'));
const {Presentation,PresentationFile,FileBlob}=await import(pathToFileURL(requireRuntime.resolve('@oai/artifact-tool')).href);
const {finalizePresentation}=await import(pathToFileURL(path.join(skillDir,'container_tools/artifact_tool_utils.mjs')).href);
const plan=JSON.parse(await fs.readFile(planPath,'utf8'));
const presentation=Presentation.create({slideSize:{width:plan.design.width,height:plan.design.height}});
for(const page of plan.slides){
  const slide=presentation.slides.add();slide.background.fill=plan.design.background;
  for(const item of page.elements){
    const shape=slide.shapes.add({name:item.name,geometry:item.kind==='text'?'textbox':item.kind,
      position:{left:item.x,top:item.y,width:item.w,height:item.h},
      fill:item.kind==='text'?'none':item.color,line:{fill:'none',width:0}});
    if(item.kind==='text'){
      shape.text=item.text;
      shape.text.style={typeface:item.font,fontSize:item.size,bold:item.bold,color:item.color,autoFit:'none',
        verticalAlignment:'top',alignment:'left'};
    }
  }
}
await fs.mkdir(buildDir,{recursive:true});await fs.mkdir(path.dirname(finalPath),{recursive:true});
const candidatePath=path.join(buildDir,'candidate.pptx');
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
await finalizePresentation({workspaceDir:process.cwd(),candidatePath,finalPath,pythonExecutable,
  integrityValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],
  requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],
  fontPolicy:{basis:'design',families:[plan.design.font,plan.design.math_font]},verifyArtifactToolImport:true,
  receiptPath:path.join(buildDir,'toolkit-validation.json')});
// Inspect the actual finalized PPTX, not just the pre-export authoring model.
const imported=await PresentationFile.importPptx(await FileBlob.load(finalPath));
await fs.mkdir(path.join(buildDir,'preview'),{recursive:true});
for(let i=0;i<plan.slides.length;i++){
  const slide=imported.slides.getItem(i);
  const png=await imported.export({slide,format:'png',scale:1});
  await fs.writeFile(path.join(buildDir,'preview',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
  const layout=await slide.export({format:'layout'});
  await fs.writeFile(path.join(buildDir,'preview',`slide-${String(i+1).padStart(2,'0')}.json`),await layout.text());
}
console.log(JSON.stringify({finalPath,slides:plan.slides.length,previewDir:path.join(buildDir,'preview')}));
