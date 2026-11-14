"""Local doorplate OCR. No filename-based labels or external recognition service."""
from __future__ import annotations
import csv, json, os, re, time, unicodedata
from pathlib import Path
from typing import Iterable
import cv2
import numpy as np
from PIL import Image, ImageOps

EXTENSIONS={'.jpg','.jpeg','.png','.bmp','.webp'}
MODEL='PP-OCRv4 / RapidOCR 1.4.4 / ONNX Runtime CPU'

def normalize(text):
    text=unicodedata.normalize('NFKC',str(text))
    text=re.sub(r'\s+','',text)
    text=text.translate(str.maketrans({'—':'-','–':'-','−':'-','－':'-','﹣':'-'}))
    return re.sub(r'(?<=\d)一(?=\d)','-',text)

def collect_paths(inputs,recursive=True,cancel=None):
    found={}; errors=[]
    def add(f):
        if f.suffix.lower() in EXTENSIONS:
            resolved=f.resolve();found[os.path.normcase(str(resolved))]=str(resolved)
    for item in inputs:
        if cancel is not None and cancel.is_set():break
        f=Path(item)
        if f.is_file():
            if f.suffix.lower() in EXTENSIONS:add(f)
            else:errors.append(f'不支持的文件格式：{f.name}')
        elif f.is_dir():
            def on_error(e):errors.append(str(e))
            for directory,dirs,names in os.walk(f,onerror=on_error,followlinks=False):
                dirs[:]=[d for d in dirs if d not in {'.venv','venv','.git','__pycache__'}] if recursive else []
                for name in sorted(names):
                    if cancel is not None and cancel.is_set():return sorted(found.values()),errors
                    add(Path(directory)/name)
        else:errors.append(f'文件或文件夹不存在：{f}')
    return sorted(found.values()),errors

def read_image(path):
    with Image.open(path) as im:
        im=ImageOps.exif_transpose(im)
        if im.mode in ('RGBA','LA') or 'transparency' in im.info:
            rgba=im.convert('RGBA'); background=Image.new('RGBA',rgba.size,'white')
            im=Image.alpha_composite(background,rgba).convert('RGB')
        else:im=im.convert('RGB')
        rgb=np.asarray(im).copy()
    if min(rgb.shape[:2])<8:raise ValueError('图片过小，无法可靠识别')
    return cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)

def empty_result(path,mode='enhanced'):
    return dict(path=str(Path(path).resolve()),filename=Path(path).name,address='',number='',
                original_address='',original_number='',raw_text='',confidence=0.,seconds=0.,
                mode=mode,chosen='原图',status='待识别',warnings=[],error='',corrected=False,
                tokens=[],candidates=[],width=0,height=0)

def group_lines(tokens):
    # Align centres to the dominant horizontal text angle; do not merge tall
    # vertical village names into the large numeric line.
    measured=[];angles=[]
    for idx,t in enumerate(tokens):
        box=np.asarray(t['box'],float);width=max(1.,float(np.linalg.norm(box[1]-box[0])));height=max(1.,float(np.linalg.norm(box[3]-box[0])))
        vertical=width/height<.65 and len(normalize(t['text']))>1
        slope=(box[1,1]-box[0,1])/max(1.,box[1,0]-box[0,0])
        if not vertical and abs(slope)<.5:angles.append(slope)
        measured.append((idx,t,box,width,height,vertical))
    slope=float(np.median(angles)) if angles else 0.;groups=[]
    for idx,t,box,width,height,vertical in sorted(measured,key=lambda v:float(v[2][:,1].mean()-slope*v[2][:,0].mean())):
        y=float(box[:,1].mean()-slope*box[:,0].mean());fontheight=width if vertical else height
        group=next((g for g in groups if not vertical and not g['vertical'] and abs(y-g['y'])<=.45*max(fontheight,g['height'])),None)
        if group is None:group={'y':y,'height':fontheight,'vertical':vertical,'items':[]};groups.append(group)
        group['items'].append((idx,t,y));group['y']=float(np.mean([v[2] for v in group['items']]));group['height']=max(group['height'],fontheight)
    result=[]
    for g in sorted(groups,key=lambda x:x['y']):
        items=sorted(g['items'],key=lambda v:min(pt[0] for pt in v[1]['box']))
        text=''.join(normalize(t['text']) for _,t,_ in items)
        score=sum(float(t['score'])*max(1,len(normalize(t['text']))) for _,t,_ in items)/max(1,sum(len(normalize(t['text'])) for _,t,_ in items))
        result.append(dict(text=text,score=score,height=g['height'],y=g['y'],vertical=g['vertical'],indices=[i for i,_,_ in items]))
    return result

def parse_tokens(tokens):
    lines=group_lines(tokens); nums=[];inline_address=''
    number_re=r'\d{1,6}(?:[-/]\d{1,6}){0,3}'
    for line in lines:
        m=re.fullmatch('('+number_re+r')(?:号|室|栋)?(?:\(临\))?',line['text'])
        if m:nums.append((line,m[1]))
    if not nums:
        for line in lines:
            m=re.fullmatch(r'(.+[\u4e00-\u9fff])('+number_re+r')(?:号|室)?',line['text'])
            if m:
                nums.append((line,m[2]));inline_address=m[1]
    chosen=max(nums,key=lambda v:(v[0]['height'],v[0]['score'])) if nums else None
    chinese=[l for l in lines if not l['vertical'] and (not chosen or l is not chosen[0]) and re.search(r'[\u4e00-\u9fff]',l['text']) and not re.search(r'电话|扫码|扫描|二维码|监督|公安|管理|服务热线|邮政编码|门牌号|公众号',l['text']) and l['text'] not in {'号','室','栋'}]
    if chosen:
        before=[l for l in chinese if l['y']<chosen[0]['y']+0.35*chosen[0]['height']]
        chinese=before or chinese
    addr=max(chinese,key=lambda l:(l['height'],-abs(l['y']-chosen[0]['y']) if chosen else 0)) if chinese else None
    address=inline_address or (addr['text'] if addr else '')
    number=chosen[1] if chosen else ''
    addr_score=addr['score'] if addr else (chosen[0]['score'] if inline_address and chosen else 0.)
    num_score=chosen[0]['score'] if chosen else 0.
    scores=[s for s in [addr_score,num_score] if s>0]
    confidence=min(scores) if scores else 0.
    ambiguity=bool(chosen and any(n!=number and l['height']>=0.75*chosen[0]['height'] for l,n in nums))
    return dict(address=address,number=number,confidence=confidence,address_score=addr_score,
                number_score=num_score,ambiguous=ambiguity,raw_text='\n'.join(l['text'] for l in lines))

def perspective_variant(image):
    h,w=image.shape[:2]; hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
    mask=cv2.inRange(hsv,np.array([85,40,25]),np.array([150,255,255]))
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((7,7),np.uint8))
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if not contours:return None
    c=max(contours,key=cv2.contourArea);area=cv2.contourArea(c)
    if area<0.20*h*w:return None
    approx=cv2.approxPolyDP(c,0.025*cv2.arcLength(c,True),True)
    if len(approx)!=4 or not cv2.isContourConvex(approx):return None
    pts=approx[:,0,:].astype(np.float32);s=pts.sum(1);d=np.diff(pts,axis=1).ravel()
    quad=np.array([pts[np.argmin(s)],pts[np.argmin(d)],pts[np.argmax(s)],pts[np.argmax(d)]],np.float32)
    if len({tuple(v) for v in quad})!=4:return None
    nw=int(max(np.linalg.norm(quad[0]-quad[1]),np.linalg.norm(quad[2]-quad[3])))
    nh=int(max(np.linalg.norm(quad[0]-quad[3]),np.linalg.norm(quad[1]-quad[2])))
    if min(nw,nh)<35 or not 0.6<nw/nh<6:return None
    target=np.array([[0,0],[nw-1,0],[nw-1,nh-1],[0,nh-1]],np.float32)
    transform=cv2.getPerspectiveTransform(quad,target)
    return cv2.warpPerspective(image,transform,(nw,nh)),np.linalg.inv(transform)

def make_variants(image,allowed=None):
    allowed=set(allowed or ['scale','contrast','perspective']);h,w=image.shape[:2]
    if 'scale' in allowed:
        factor=min(4.,max(1.5,360/min(h,w)),1800/max(h,w))
        if factor>1.05:
            nw,nh=int(w*factor),int(h*factor)
            scaled=cv2.resize(image,(nw,nh),interpolation=cv2.INTER_CUBIC)
            yield '放大',scaled,np.diag([w/nw,h/nh,1.])
    if 'contrast' in allowed:
        lab=cv2.cvtColor(image,cv2.COLOR_BGR2LAB);l,a,b=cv2.split(lab)
        enhanced=cv2.cvtColor(cv2.merge((cv2.createCLAHE(clipLimit=2.,tileGridSize=(8,8)).apply(l),a,b)),cv2.COLOR_LAB2BGR)
        yield '对比度增强',enhanced,np.eye(3)
    if 'perspective' in allowed:
        warp=perspective_variant(image)
        if warp is not None:yield '透视校正',warp[0],warp[1]

class DoorplateEngine:
    def __init__(self):
        from rapidocr_onnxruntime import RapidOCR
        self.ocr=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=1,text_score=0.3)
    def candidate(self,image,name,inverse):
        raw,_=self.ocr(image);tokens=[]
        for box,text,score in raw or []:
            box=cv2.perspectiveTransform(np.asarray(box,np.float32)[None,:,:],np.asarray(inverse,np.float64))[0]
            tokens.append(dict(text=text,score=float(score),box=box.astype(float).tolist()))
        parsed=parse_tokens(tokens)
        return dict(parsed,tokens=tokens,name=name)
    def recognize(self,path,mode='enhanced',allowed=None):
        start=time.perf_counter();record=empty_result(path,mode)
        try:
            image=read_image(path);h,w=image.shape[:2];record.update(width=w,height=h)
            base=self.candidate(image,'原图',np.eye(3));candidates=[base]
            trigger=not base['address'] or not base['number'] or base['confidence']<0.90 or min(h,w)<120
            if mode=='enhanced' and trigger:
                for name,variant,inverse in make_variants(image,allowed):
                    candidates.append(self.candidate(variant,name,inverse))
            chosen=base
            for c in candidates[1:]:
                completeness=int(bool(c['address']))+int(bool(c['number']))
                old=int(bool(chosen['address']))+int(bool(chosen['number']))
                if completeness>old or (completeness==old and c['confidence']>chosen['confidence']+0.025):chosen=c
            warnings=[]
            if not chosen['number']:warnings.append('未找到门牌号')
            if not chosen['address']:warnings.append('未找到地址文字')
            if chosen['confidence']<0.85:warnings.append('识别得分偏低')
            if chosen['ambiguous']:warnings.append('存在多个较大数字候选')
            if min(h,w)<80:warnings.append('图片分辨率很低')
            reliable=[c for c in candidates if c['confidence']>=0.85 and c['number']]
            if len({(c['address'],c['number']) for c in reliable})>1:warnings.append('不同处理候选存在分歧')
            record.update(address=chosen['address'],number=chosen['number'],original_address=chosen['address'],
                          original_number=chosen['number'],raw_text=chosen['raw_text'],confidence=chosen['confidence'],
                          chosen=chosen['name'],tokens=chosen['tokens'],warnings=warnings,
                          status='待复核' if warnings else '已完成',
                          candidates=[{k:v for k,v in c.items() if k not in {'tokens'}} for c in candidates])
        except Exception as e:record.update(status='失败',error=f'{type(e).__name__}: {e}')
        record['seconds']=time.perf_counter()-start
        return record

def export_results(records,destination):
    destination=Path(destination)
    if destination.suffix.lower()=='.json':
        destination.write_text(json.dumps({'model':MODEL,'records':records},ensure_ascii=False,indent=2),encoding='utf-8')
    else:
        fields=['filename','path','address','number','original_address','original_number','corrected','raw_text','confidence','seconds','mode','chosen','status','warnings','error']
        with destination.open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',quoting=csv.QUOTE_ALL);writer.writeheader()
            for record in records:
                row=record.copy();row['warnings']='；'.join(row.get('warnings',[]));writer.writerow(row)
