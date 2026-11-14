from __future__ import annotations
import argparse,os,queue,sys,threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from PIL import Image,ImageDraw,ImageFont,ImageTk
from tkinterdnd2 import DND_FILES,TkinterDnD
from core import DoorplateEngine,collect_paths,empty_result,export_results,read_image
import cv2
from ui_layout import WorkbenchUI

def enable_dpi_awareness():
    if sys.platform=='win32':
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:pass

class DoorplateApp(WorkbenchUI):
    def __init__(self,root):
        self.root=root;self.root.title('门牌识别工作台');self.root.geometry(f'{min(1380,root.winfo_screenwidth()-80)}x{min(880,root.winfo_screenheight()-100)}');self.root.minsize(min(1120,root.winfo_screenwidth()-80),min(720,root.winfo_screenheight()-100))
        self.root.configure(bg='#F3F6FB');self.records={};self.events=queue.Queue();self.executor=ThreadPoolExecutor(max_workers=1)
        self.engine=None;self.busy=False;self.closing=False;self.cancel_event=threading.Event();self.pending_imports=[]
        self.current=None;self.preview=None;self.photo=None;self.completed=0;self.total=0;self.auto_start=False
        self.recursive=tk.BooleanVar(value=True);self.auto=tk.BooleanVar(value=True);self.mode=tk.StringVar(value='门牌增强')
        self.address=tk.StringVar();self.number=tk.StringVar();self.status=tk.StringVar(value='拖入图片或文件夹，开始本地识别')
        self._build();self.root.protocol('WM_DELETE_WINDOW',self.close);self.root.after(60,self.poll)
    def key(self,path):return os.path.normcase(str(Path(path).resolve()))
    def drop(self,event):
        try:self.import_paths(list(self.root.tk.splitlist(event.data)))
        except Exception as e:messagebox.showerror('导入失败',str(e))
        return event.action
    def pick_files(self):
        files=filedialog.askopenfilenames(title='选择门牌图片',filetypes=[('图片','*.jpg *.jpeg *.png *.bmp *.webp'),('所有文件','*.*')])
        if files:self.import_paths(list(files))
    def pick_folder(self):
        directory=filedialog.askdirectory(title='选择图片文件夹')
        if directory:self.import_paths([directory])
    def course_files(self):
        base=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).parent
        candidates=[base.parent/'实践素材1—门牌号识别',base.parent.parent/'实践素材1—门牌号识别',base/'实践素材1—门牌号识别',base.parent.parent.parent/'实践素材1—门牌号识别']
        directory=next((p for p in candidates if p.is_dir()),None)
        if directory:self.import_paths([str(directory)])
        else:self.pick_folder()
    def import_paths(self,paths):
        if self.busy:
            self.pending_imports.extend(paths);self.status.set('已加入导入队列，当前任务结束后扫描');return
        self.set_busy(True);self.cancel_event=threading.Event();cancel=self.cancel_event;recursive=self.recursive.get()
        def scan():
            try:
                files,errors=collect_paths(paths,recursive,cancel);self.events.put(('scanned',files,errors))
            except Exception as e:self.events.put(('fatal',str(e)))
            finally:self.events.put(('done','scan'))
        self.executor.submit(scan);self.status.set('正在扫描图片文件…')
    def start(self):
        if self.busy:return
        paths=[k for k,r in self.records.items() if r['status'] in {'待识别','失败'}]
        if not paths:
            if self.records and messagebox.askyesno('重新识别','所有图片已有结果。重新识别会覆盖当前结果，包括人工修正。'):
                paths=list(self.records)
            else:return
        self.set_busy(True);self.cancel_event=threading.Event();cancel=self.cancel_event
        mode='base' if self.mode.get()=='基础 OCR' else 'enhanced';self.completed=0;self.total=len(paths);self.progress.configure(maximum=self.total,value=0)
        self.status.set('正在加载本地识别模型…')
        def run():
            try:
                if self.engine is None:self.engine=DoorplateEngine()
                for key in paths:
                    if cancel.is_set():break
                    self.events.put(('processing',key));result=self.engine.recognize(self.records[key]['path'],mode)
                    self.events.put(('result',key,result))
            except Exception as e:self.events.put(('fatal',str(e)))
            finally:self.events.put(('done','recognition'))
        self.executor.submit(run)
    def set_busy(self,value):
        self.busy=value;self.start_button.configure(state='disabled' if value else 'normal');self.clear_button.configure(state='disabled' if value else 'normal')
        self.cancel_button.configure(state='normal' if value else 'disabled');self.save_button.configure(state='disabled' if value else 'normal')
    def cancel(self):self.cancel_event.set();self.status.set('正在取消：完成当前图片后停止，保留已完成结果')
    def update_row(self,key):self._update_row_visual(key)
    def poll(self):
        try:
            while True:
                event=self.events.get_nowait();kind=event[0]
                if kind=='scanned':
                    new_count=0
                    for path in event[1]:
                        key=self.key(path)
                        if key not in self.records:self.records[key]=empty_result(path);self.update_row(key);new_count+=1
                    self.status.set(f'共导入 {len(self.records)} 张图片'+(f'；{len(event[2])} 项提示' if event[2] else ''))
                    self.auto_start=self.auto.get() and new_count>0
                    if event[2]:messagebox.showwarning('导入提示','\n'.join(event[2][:10]))
                    if not self.current and self.records:
                        visible=self.tree.get_children()
                        if visible:self.tree.selection_set(visible[0]);self.select()
                elif kind=='processing':
                    self.records[event[1]]['status']='识别中';self.update_row(event[1])
                elif kind=='result':
                    self.records[event[1]]=event[2];self.update_row(event[1]);self.completed+=1;self.progress.configure(value=self.completed)
                    self.status.set(f"识别进度 {self.completed}/{self.total} · {event[2]['address']} {event[2]['number']}")
                    if self.current==event[1]:self.select()
                elif kind=='fatal':
                    self.auto_start=False;self.status.set('任务失败：'+event[1]);messagebox.showerror('任务失败',event[1])
                elif kind=='done':
                    cancelled=self.cancel_event.is_set();self.set_busy(False)
                    if event[1]=='recognition':
                        counts={s:sum(r['status']==s for r in self.records.values()) for s in ['已完成','已修正','待复核','失败','待识别']}
                        self.status.set(('已取消；' if cancelled else '识别完成；')+'，'.join(f'{s} {n}' for s,n in counts.items()))
                    if self.closing:self.executor.shutdown(wait=False);self.root.destroy();return
                    if self.pending_imports:
                        pending=self.pending_imports;self.pending_imports=[];self.import_paths(pending)
                    elif event[1]=='scan' and self.auto_start and not cancelled:
                        self.auto_start=False;self.root.after(10,self.start)
        except queue.Empty:pass
        self.root.after(60,self.poll)
    def correct(self):
        if self.busy or not self.current:return
        r=self.records[self.current]
        if r['status'] in {'待识别','失败','识别中'}:messagebox.showinfo('提示','请先完成该图片的识别');return
        r.update(address=self.address.get().strip(),number=self.number.get().strip(),corrected=True,status='已修正');self.update_row(self.current)
        self.select();self.filter_rows();self.status.set('修正已保存；请导出结果以保留原始字段与修正内容')
    def export(self):
        if not self.records:messagebox.showinfo('提示','请先导入图片');return
        path=filedialog.asksaveasfilename(title='导出识别结果',defaultextension='.csv',initialfile='门牌识别结果.csv',filetypes=[('CSV 表格','*.csv'),('JSON 完整记录','*.json')])
        if path:
            try:export_results(list(self.records.values()),path);self.status.set('已导出：'+path)
            except Exception as e:messagebox.showerror('导出失败',str(e))
    def clear(self):
        if self.busy:return
        if self.records and not messagebox.askyesno('清空结果','清空当前列表？未导出的识别结果和人工修正将丢失。'):return
        self.tree.delete(*list(self.records));self.records.clear();self.query.set('');self.filter_value.set('全部图片');self._reset_selection();self._refresh_stats();self.progress.configure(value=0);self.status.set('列表已清空，可以开始新一批识别')
    def close(self):
        self.closing=True
        if self.busy:self.cancel_event.set();self.root.withdraw()
        else:self.executor.shutdown(wait=False);self.root.destroy()

def main():
    if '--offline' in sys.argv:
        import socket
        def forbidden_network(*args,**kwargs):raise RuntimeError('Offline verification: network connections are disabled')
        socket.socket.connect=forbidden_network;socket.socket.connect_ex=forbidden_network;socket.socket.sendto=forbidden_network;socket.create_connection=forbidden_network
    if '--self-test' in sys.argv:
        parser=argparse.ArgumentParser();parser.add_argument('--self-test',required=True);parser.add_argument('--output',required=True);parser.add_argument('--offline',action='store_true')
        args=parser.parse_args();result=DoorplateEngine().recognize(args.self_test)
        export_results([result],args.output);return 0 if result['status']!='失败' else 1
    enable_dpi_awareness();root=TkinterDnD.Tk();app=DoorplateApp(root)
    if '--verify-ui' in sys.argv:
        parser=argparse.ArgumentParser();parser.add_argument('--verify-ui',required=True);parser.add_argument('--output',required=True);parser.add_argument('--offline',action='store_true');parser.add_argument('--screenshot')
        args=parser.parse_args();root.attributes('-topmost',True);root.after(200,lambda:app.import_paths([args.verify_ui]))
        def finish():
            if app.records and not app.busy and all(r['status'] not in {'待识别','识别中'} for r in app.records.values()):
                export_results(list(app.records.values()),args.output)
                import json,rapidocr_onnxruntime,onnxruntime,numpy,tkinterdnd2
                verification={'frozen':bool(getattr(sys,'frozen',False)),'network_connections_disabled':args.offline,'executable':sys.executable,'module_paths':{m.__name__:m.__file__ for m in [rapidocr_onnxruntime,onnxruntime,numpy,tkinterdnd2]},'records':len(app.records),'failures':sum(r['status']=='失败' for r in app.records.values()),'path_environment':os.environ.get('PATH','')}
                Path(args.output).with_suffix('.verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
                last=next(reversed(app.records));app.tree.selection_set(last);app.tree.see(last);app.select();root.lift();root.update()
                if args.screenshot:
                    from PIL import ImageGrab
                    root.update();ImageGrab.grab(bbox=(root.winfo_rootx(),root.winfo_rooty(),root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(args.screenshot)
                app.close()
            else:root.after(150,finish)
        root.after(600,finish)
    root.mainloop();return 0
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        import traceback
        error=traceback.format_exc()
        error_path=(Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).parent)/'门牌识别错误.log'
        try:error_path.write_text(error,encoding='utf-8')
        except OSError:
            import tempfile
            error_path=Path(tempfile.gettempdir())/'门牌识别错误.log';error_path.write_text(error,encoding='utf-8')
        if not any(flag in sys.argv for flag in ['--verify-ui','--self-test']):
            try:messagebox.showerror('软件启动失败',f'{exc}\n\n错误详情已保存：{error_path}')
            except Exception:pass
        sys.exit(1)
