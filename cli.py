import argparse,json,sys,time
from pathlib import Path
from core import DoorplateEngine,collect_paths,export_results

def main():
    p=argparse.ArgumentParser(description='本地中文与数字门牌识别')
    p.add_argument('--input',nargs='+',required=True,help='图片或文件夹路径')
    p.add_argument('--output',required=True,help='输出 .csv 或 .json')
    p.add_argument('--mode',choices=['base','enhanced'],default='enhanced')
    p.add_argument('--variant',choices=['all','scale','contrast','perspective'],default='all')
    p.add_argument('--no-recursive',action='store_true')
    args=p.parse_args();paths,errors=collect_paths(args.input,not args.no_recursive)
    for error in errors:print(error,file=sys.stderr)
    if not paths:print('没有找到支持的图片',file=sys.stderr);return 2
    engine=DoorplateEngine();results=[]
    for i,path in enumerate(paths,1):
        r=engine.recognize(path,args.mode,None if args.variant=='all' else [args.variant]);results.append(r)
        print(f"{i}/{len(paths)} {r['filename']}  {r['address']} {r['number']}  {r['status']}",flush=True)
    export_results(results,args.output)
    return 0 if all(r['status']!='失败' for r in results) else 1
if __name__=='__main__':sys.exit(main())
