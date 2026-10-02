"""Legacy CLI wrapper; importing it never opens or writes a document."""
from pathlib import Path
from academic_os.curriculum_ingestion.core import extract_pages as extract_document_pages

def extract_pages(start_page, end_page, pdf_path):
    return extract_document_pages(pdf_path,start_page,end_page).text

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--pdf',type=Path,default=Path('international-gcse-in-mathematics-spec-a.pdf'));p.add_argument('--output-dir',type=Path,default=Path('output'))
    args=p.parse_args(argv);args.output_dir.mkdir(parents=True,exist_ok=True)
    for tier,start,end in [('foundation',21,22),('higher',37,38)]:
        destination=args.output_dir/f'topic2_{tier}_raw.txt'
        destination.write_text(extract_pages(start,end,args.pdf),encoding='utf-8');print(destination)
    return 0

if __name__=='__main__':raise SystemExit(main())
