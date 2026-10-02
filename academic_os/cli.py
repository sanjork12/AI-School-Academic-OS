"""Local-operator CLI; OS account + database write access is the trust boundary."""
import argparse
import getpass
import json
import sqlite3
from pathlib import Path
from .storage import Store
from .service import Service
from .examples.q2 import build_candidates,DEFAULT_SOURCES,ROOTS
from .models import normalise
from .sources import register_candidate,extract_candidate
from .publication import TARGETS
from .review_bundles import BUNDLES
from .source_bundles import ALL_SOURCE_BUNDLES as SOURCE_BUNDLES

def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',type=Path,default=Path('var/academic_os.sqlite3'))
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init')
    sub.add_parser('lesson-profiles')
    p=sub.add_parser('render-profiled-presentations');p.add_argument('topic_key',choices=['standard-deviation'])
    p.add_argument('--snapshot',action='append',dest='snapshot_ids');p.add_argument('--output-dir',type=Path,required=True)
    p=sub.add_parser('validate-profiled-content');p.add_argument('topic_key',choices=['standard-deviation'])
    p.add_argument('--snapshot',action='append',dest='snapshot_ids');p.add_argument('--output-dir',type=Path)
    p=sub.add_parser('author-profiled-content');p.add_argument('topic_key',choices=['standard-deviation'])
    p.add_argument('--snapshot',action='append',dest='snapshot_ids');p.add_argument('--output-dir',type=Path)
    p=sub.add_parser('profile-pedagogy');p.add_argument('topic_key',choices=['standard-deviation'])
    p.add_argument('--snapshot',action='append',dest='snapshot_ids');p.add_argument('--output-dir',type=Path)
    p=sub.add_parser('import-q2');p.add_argument('--source-dir',type=Path,default=DEFAULT_SOURCES);p.add_argument('--request-id',required=True)
    p=sub.add_parser('stage');p.add_argument('--file',required=True);p.add_argument('--request-id',required=True)
    p=sub.add_parser('parse-q2');p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('plan-q3-2023');p.add_argument('--output',type=Path,required=True);p.add_argument('--source-dir',type=Path)
    p=sub.add_parser('semantic-q2');p.add_argument('--plan-output',type=Path)
    for name in ['review-sources','review-source','review-bundles','review-bundle']:
        p=sub.add_parser(name);p.add_argument('--json',action='store_true');p.add_argument('--details',action='store_true')
        if name in ('review-bundle','review-source'):
            p.add_argument('bundle_id',choices=SOURCE_BUNDLES if name=='review-source' else BUNDLES);p.add_argument('--save-ticket',type=Path)
    p=sub.add_parser('decide-bundle');p.add_argument('bundle_id',choices=BUNDLES)
    p.add_argument('action',choices=['approve','reject','revise']);p.add_argument('--ticket',required=True)
    p.add_argument('--reason',required=True);p.add_argument('--request-id',required=True)
    p=sub.add_parser('decide-source');p.add_argument('bundle_id',choices=SOURCE_BUNDLES)
    p.add_argument('action',choices=['verify','reject']);p.add_argument('--ticket',required=True)
    p.add_argument('--reason',required=True);p.add_argument('--request-id',required=True)
    p=sub.add_parser('review-unresolved');p.add_argument('proposal');p.add_argument('--target',choices=TARGETS,required=True)
    p.add_argument('--save-ticket',type=Path);p.add_argument('--json',action='store_true')
    p=sub.add_parser('decide-unresolved');p.add_argument('proposal');p.add_argument('action',choices=['defer','reopen'])
    p.add_argument('--target',choices=TARGETS,required=True);p.add_argument('--ticket',required=True)
    p.add_argument('--reason',required=True);p.add_argument('--request-id',required=True)
    p=sub.add_parser('register-source')
    for field in ['id','path','title','source-type','curriculum','version-label','identity-basis','request-id']:p.add_argument('--'+field,required=True)
    p=sub.add_parser('extract-locator')
    for field in ['source','id','label','summary','request-id']:p.add_argument('--'+field,required=True)
    p.add_argument('--page',type=int,required=True)
    sub.add_parser('pending')
    p=sub.add_parser('inspect');p.add_argument('key')
    p=sub.add_parser('review');p.add_argument('key');p.add_argument('action',choices=['verify','approve','reject','revise','revoke','supersede'])
    for field in ['reason','expected-version','expected-dependencies','expected-decision','request-id']:p.add_argument('--'+field,required=True)
    p.add_argument('--replacement-action',choices=['verify','approve','reject','revise'])
    for name in ['check','publish']:
        p=sub.add_parser(name);selection=p.add_mutually_exclusive_group()
        selection.add_argument('--root',action='append',dest='roots');selection.add_argument('--target',choices=TARGETS)
        if name=='publish':p.add_argument('--output',type=Path)
    p=sub.add_parser('snapshot');p.add_argument('snapshot_id');p.add_argument('--output',type=Path)
    p=sub.add_parser('render-presentation');p.add_argument('topic_key',choices=['standard-deviation'])
    p.add_argument('--design',choices=['classic','classroom-v2'],default='classic')
    p.add_argument('--snapshot',action='append',dest='snapshot_ids');p.add_argument('--output-dir',type=Path,required=True)
    p=sub.add_parser('validate-authored-content');p.add_argument('topic_key',choices=['standard-deviation'])
    p.add_argument('--snapshot',action='append',dest='snapshot_ids');p.add_argument('--json',action='store_true')
    p.add_argument('--output',type=Path)
    p=sub.add_parser('author-teaching-content');p.add_argument('topic_key',choices=['standard-deviation'])
    p.add_argument('--snapshot',action='append',dest='snapshot_ids');p.add_argument('--json',action='store_true')
    p.add_argument('--output',type=Path)
    p=sub.add_parser('validate-pedagogy');p.add_argument('topic_key',choices=['standard-deviation'])
    p.add_argument('--snapshot',action='append',dest='snapshot_ids');p.add_argument('--json',action='store_true')
    p.add_argument('--output',type=Path)
    p=sub.add_parser('pedagogical-specification');p.add_argument('topic_key',choices=['standard-deviation'])
    p.add_argument('--snapshot',action='append',dest='snapshot_ids');p.add_argument('--json',action='store_true')
    p.add_argument('--output',type=Path)
    p=sub.add_parser('learning-specification');p.add_argument('topic_key',choices=['standard-deviation'])
    p.add_argument('--snapshot',action='append',dest='snapshot_ids');p.add_argument('--json',action='store_true')
    p.add_argument('--output',type=Path)
    p=sub.add_parser('assessment-intelligence');p.add_argument('topic_key',choices=['standard-deviation'])
    p.add_argument('--snapshot',action='append',dest='snapshot_ids');p.add_argument('--json',action='store_true')
    p.add_argument('--output',type=Path)
    p=sub.add_parser('teacher-topic');p.add_argument('topic_key',choices=['standard-deviation'])
    p.add_argument('--snapshot',action='append',dest='snapshot_ids');p.add_argument('--json',action='store_true')
    p.add_argument('--output',type=Path)
    args=parser.parse_args(argv);store=None
    try:
        if args.command=='render-profiled-presentations':
            from .profile_presentation_service import ProfilePresentationService
            from .product_catalog import PROTECTED_SNAPSHOTS
            result=ProfilePresentationService(args.db).render(args.topic_key,args.snapshot_ids or PROTECTED_SNAPSHOTS,args.output_dir)
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0
        if args.command=='lesson-profiles':
            from .lesson_profiles import KEYS,lesson_profile
            print(json.dumps({k:lesson_profile(k).model_dump(mode='json') for k in KEYS},ensure_ascii=False,indent=2));return 0
        if args.command=='validate-profiled-content':
            from .profiled_validation_service import ProfiledContentValidationService,save_profiled_validation
            from .product_catalog import PROTECTED_SNAPSHOTS
            result=ProfiledContentValidationService(args.db).read_profiles(args.topic_key,args.snapshot_ids or PROTECTED_SNAPSHOTS)
            if args.output_dir:print(json.dumps({'files':save_profiled_validation(result,args.output_dir)},ensure_ascii=False,indent=2))
            else:print(json.dumps({k:v.model_dump(mode='json') for k,v in result.reports.items()},ensure_ascii=False,indent=2))
            return 0 if all(v.renderer_readiness.ready_for_rendering for v in result.reports.values()) else 1
        if args.command=='author-profiled-content':
            from .profiled_content_service import ProfiledContentService,save_profiled_content
            from .product_catalog import PROTECTED_SNAPSHOTS
            result=ProfiledContentService(args.db).read_profiles(args.topic_key,args.snapshot_ids or PROTECTED_SNAPSHOTS)
            if args.output_dir:print(json.dumps({'files':save_profiled_content(result,args.output_dir)},ensure_ascii=False,indent=2))
            else:print(json.dumps({k:v.model_dump(mode='json') for k,v in result.packages.items()},ensure_ascii=False,indent=2))
            return 0
        if args.command=='profile-pedagogy':
            from .lesson_profile_service import LessonProfileService,save_profile_read
            from .product_catalog import PROTECTED_SNAPSHOTS
            result=LessonProfileService(args.db).read_profiles(args.topic_key,args.snapshot_ids or PROTECTED_SNAPSHOTS)
            if args.output_dir:print(json.dumps({'files':save_profile_read(result,args.output_dir)},ensure_ascii=False,indent=2))
            else:print(json.dumps({k:v.model_dump(mode='json') for k,v in result.views.items()},ensure_ascii=False,indent=2))
            return 0
        if args.command=='render-presentation':
            from .presentation_service import PresentationService
            from .product_catalog import PROTECTED_SNAPSHOTS
            result=PresentationService(args.db).render(args.topic_key,args.snapshot_ids or PROTECTED_SNAPSHOTS,args.output_dir,design=args.design)
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0
        if args.command in ('teacher-topic','assessment-intelligence','learning-specification','pedagogical-specification','validate-pedagogy','author-teaching-content','validate-authored-content'):
            from .product_service import AcademicProductService
            from .product_catalog import PROTECTED_SNAPSHOTS
            from .product_rendering import teacher_topic_text
            if args.command=='validate-authored-content':
                from .content_validation_service import AuthoredContentValidationService,content_validation_text
                view=AuthoredContentValidationService(args.db).read_topic(args.topic_key,args.snapshot_ids or PROTECTED_SNAPSHOTS).view
                render=content_validation_text
            elif args.command=='author-teaching-content':
                from .authored_service import AuthoredTeachingService,authored_text
                view=AuthoredTeachingService(args.db).read_topic(args.topic_key,args.snapshot_ids or PROTECTED_SNAPSHOTS).view
                render=authored_text
            elif args.command=='validate-pedagogy':
                from .pedagogical_validation import PedagogicalValidationService,validation_text
                view=PedagogicalValidationService(args.db).read_topic(args.topic_key,args.snapshot_ids or PROTECTED_SNAPSHOTS).view
                render=validation_text
            elif args.command=='pedagogical-specification':
                from .pedagogical_service import PedagogicalSpecificationService,pedagogical_specification_text
                view=PedagogicalSpecificationService(args.db).read_topic(args.topic_key,args.snapshot_ids or PROTECTED_SNAPSHOTS).view
                render=pedagogical_specification_text
            elif args.command=='learning-specification':
                from .learning_service import LearningSpecificationService
                from .learning_rendering import learning_specification_text
                view=LearningSpecificationService(args.db).read_topic(args.topic_key,args.snapshot_ids or PROTECTED_SNAPSHOTS).view
                render=learning_specification_text
            elif args.command=='assessment-intelligence':
                from .assessment_intelligence import AssessmentIntelligenceService,intelligence_text
                view=AssessmentIntelligenceService(args.db).read_topic(args.topic_key,args.snapshot_ids or PROTECTED_SNAPSHOTS).view
                render=intelligence_text
            else:
                view=AcademicProductService(args.db).get_topic_view(args.topic_key,args.snapshot_ids or PROTECTED_SNAPSHOTS)
                render=teacher_topic_text
            if args.output:
                args.output.parent.mkdir(parents=True,exist_ok=True)
                try:
                    with args.output.open('x',encoding='utf-8',newline='\n') as out:out.write(view.serialize())
                except FileExistsError:
                    if args.output.read_bytes()!=view.serialize().encode('utf-8'):
                        raise ValueError('Output already exists with different content; choose a new product artifact path')
            print(view.serialize() if args.json else render(view),end='' if args.json else '\n')
            if args.command=='validate-authored-content':return 0 if view.renderer_readiness.ready_for_rendering else 2
            return 2 if args.command=='validate-pedagogy' and not view.authoring_readiness.ready_for_content_authoring else 0
        store=Store(args.db);service=Service(store);exitcode=0
        if args.command=='init':result={'schema_version':1,'trust_boundary':'Local OS operator and SQLite file ownership; no production authentication'}
        elif args.command=='import-q2':
            items=build_candidates(args.source_dir);result=service.stage(items,{normalise(x)[0]:None for x in items},args.request_id)
        elif args.command=='stage':
            bundle=load(args.file)
            if set(bundle)!={'items','expected_heads'}:raise ValueError('Stage document requires only items and expected_heads; no trust credentials')
            result=service.stage(bundle['items'],bundle['expected_heads'],args.request_id)
        elif args.command=='parse-q2':
            result=service.plan_q2()
            args.output.parent.mkdir(parents=True,exist_ok=True)
            with args.output.open('x',encoding='utf-8') as out:
                json.dump(result,out,ensure_ascii=False,indent=2)
            result={'candidate_file':str(args.output.resolve()),'objects':len(result['items']),'notice':'Candidate plan only; use stage to persist, then human review.'}
        elif args.command=='plan-q3-2023':
            from .q3_pipeline import plan_q3
            with store.transaction('DEFERRED'):
                result=plan_q3(store.graph(),store.decisions(),args.source_dir)
            args.output.parent.mkdir(parents=True,exist_ok=True)
            with args.output.open('x',encoding='utf-8') as out:json.dump(result,out,ensure_ascii=False,indent=2)
            result={'candidate_file':str(args.output.resolve()),'objects':len(result['items']),'notice':'Pending candidates only. Use stage with the saved plan; no decisions generated.'}
        elif args.command=='semantic-q2':
            if args.plan_output:
                result=service.plan_q2_semantics()
                args.plan_output.parent.mkdir(parents=True,exist_ok=True)
                with args.plan_output.open('x',encoding='utf-8') as out:json.dump(result,out,ensure_ascii=False,indent=2)
                result={'candidate_file':str(args.plan_output.resolve()),'objects':len(result['items']),'notice':'P1A candidate plan; stage and operator review still required.'}
            else:
                result=service.q2_semantics_report()
                exitcode=0 if result['architecture_valid'] else 2
        elif args.command in ['review-sources','review-source','review-bundles','review-bundle']:
            from .review_rendering import sources_text,bundles_text
            if args.command=='review-source':
                result=service.review_source(args.bundle_id);rendered=sources_text([result],args.details)
                if args.save_ticket:
                    args.save_ticket.parent.mkdir(parents=True,exist_ok=True)
                    with args.save_ticket.open('x',encoding='utf-8') as out:json.dump(result['review_ticket'],out,ensure_ascii=False,indent=2)
            elif args.command=='review-sources':
                result=service.review_sources();rendered=sources_text(result,args.details)
            else:
                result=service.review_bundles(args.bundle_id if args.command=='review-bundle' else None)
                rendered=bundles_text([result] if args.command=='review-bundle' else result,args.details)
                if args.command=='review-bundle' and args.save_ticket:
                    args.save_ticket.parent.mkdir(parents=True,exist_ok=True)
                    with args.save_ticket.open('x',encoding='utf-8') as out:json.dump(result['review_ticket'],out,ensure_ascii=False,indent=2)
            if not args.json:
                print(rendered);return 0
        elif args.command=='decide-source':
            result=service.review_source_bundle(args.bundle_id,args.action,'local-os:'+getpass.getuser(),args.reason,load(args.ticket),args.request_id)
        elif args.command=='decide-bundle':
            result=service.review_bundle(args.bundle_id,args.action,'local-os:'+getpass.getuser(),args.reason,load(args.ticket),args.request_id)
        elif args.command in ('review-unresolved','decide-unresolved'):
            key=args.proposal if args.proposal.startswith('proposal:') else 'proposal:'+args.proposal
            if args.command=='review-unresolved':
                result=service.review_unresolved(key,args.target)
                if args.save_ticket:
                    args.save_ticket.parent.mkdir(parents=True,exist_ok=True)
                    with args.save_ticket.open('x',encoding='utf-8') as out:json.dump(result['review_ticket'],out,ensure_ascii=False,indent=2)
                if not args.json:
                    from .review_rendering import unresolved_text
                    print(unresolved_text(result));return 0
            else:
                result=service.decide_unresolved(key,args.target,args.action,'local-os:'+getpass.getuser(),args.reason,load(args.ticket),args.request_id)
        elif args.command=='register-source':
            raw=register_candidate(args.id,args.path,args.title,args.source_type,args.curriculum,args.version_label,args.identity_basis)
            result=service.stage([raw],{normalise(raw)[0]:None},args.request_id)
        elif args.command=='extract-locator':
            src=service.inspect('source:'+args.source)
            raw=extract_candidate(src['record'],src['version'],args.id,args.page,args.label,args.summary)
            result=service.stage([raw],{normalise(raw)[0]:None},args.request_id)
        elif args.command=='pending':result=[x for x in service.inspect() if x['state'] not in ['approve','verify']]
        elif args.command=='inspect':result=service.inspect(args.key)
        elif args.command=='review':
            result=service.review(args.key,args.action,'local-os:'+getpass.getuser(),args.reason,args.expected_version,
                args.expected_dependencies,None if args.expected_decision=='none' else args.expected_decision,args.request_id,args.replacement_action)
        elif args.command=='check':
            result=service.check_target(args.target) if args.target else service.check(args.roots or ROOTS)
            exitcode=0 if result['publishable'] else 2
        elif args.command=='publish':
            result=service.publish_target(args.target) if args.target else service.publish(args.roots or ROOTS)
            if args.output:result.update(service.export(result['snapshot_id'],args.output))
        elif args.command=='snapshot':
            result=service.export(args.snapshot_id,args.output) if args.output else service.snapshot(args.snapshot_id)
            if result.get('usable') is False:exitcode=2
        print(json.dumps(result,ensure_ascii=False,indent=2));return exitcode
    except (ValueError,OSError,KeyError,sqlite3.Error) as error:
        print(json.dumps({'error':str(error)},ensure_ascii=False));return 1
    finally:
        if store:store.close()

if __name__=='__main__':raise SystemExit(main())
