"""Presentation layer; recognition and exported record formats remain in core.py."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from tkinterdnd2 import DND_FILES
import cv2
from core import read_image
from ui_components import ModernButton, RoundedCard, checkbox_images, rounded_rect, FONT

BG='#F5F3FC';INK='#202B43';MUTED='#5A536A';BLUE='#4868F5';PURPLE='#8B5CF6';TEAL='#14B8A6';NAVY='#192540'
NOTE='#514866';TEXT_BLUE='#3557BA';TEXT_TEAL='#087B70';TEXT_AMBER='#936014';TEXT_ROSE='#AF3658'
PRIMARY_GRADIENT=('#3F5CE3','#7545D5');CYAN='#2699BC'

class WorkbenchUI:
    def _label(self,parent,text,size=14,color=INK,bold=False,**kwargs):
        return tk.Label(parent,text=text,bg=parent.cget('bg'),fg=color,
                        font=(FONT,-size,'bold' if bold else 'normal'),**kwargs)
    def _card(self,parent,**kwargs):
        return RoundedCard(parent,surface=BG,**kwargs)
    def _button(self,parent,text,command,width=100,primary=False,**kwargs):
        return ModernButton(parent,text,command,width=width,surface=parent.cget('bg'),
            color=PRIMARY_GRADIENT[0] if primary else '#F2EEFC',foreground='white' if primary else '#49395F',
            hover='#324DC8' if primary else '#E8E3F8',border='' if primary else '#CDD2E9',
            gradient=PRIMARY_GRADIENT if primary else None,**kwargs)
    def _build(self):
        self.query=tk.StringVar();self.filter_value=tk.StringVar(value='全部图片')
        self.show_boxes=tk.BooleanVar(value=True);self.zoom_mode='fit';self.zoom_factor=1.0;self.pan=[0,0]
        self._drag_origin=None
        self.root.configure(bg=BG)
        style=ttk.Style(self.root);style.theme_use('clam')
        style.configure('.',font=(FONT,-14),background=BG,foreground=INK)
        style.configure('TFrame',background=BG)
        style.configure('Card.TFrame',background='white')
        style.configure('TCombobox',padding=6,arrowsize=12,fieldbackground='#FCFAFF',background='#EEE7FC',bordercolor='#CBD4E8',arrowcolor=NOTE)
        style.map('TCombobox',fieldbackground=[('readonly','white')],selectbackground=[('readonly','white')],selectforeground=[('readonly',INK)])
        style.configure('Work.Treeview',font=(FONT,-14),rowheight=34,background='white',fieldbackground='white',
                        foreground=INK,borderwidth=0,relief='flat')
        style.configure('Work.Treeview.Heading',font=(FONT,-13,'bold'),background='#EEE8FC',foreground='#4B396A',
                        padding=(10,10),borderwidth=0,relief='flat')
        style.map('Work.Treeview',background=[('selected','#E5E8FC')],foreground=[('selected','#41318B')])
        style.map('Work.Treeview.Heading',background=[('active','#E4DDF8')])
        style.configure('Vertical.TScrollbar',background='#D7CCE9',troughcolor='#F8F6FC',borderwidth=0,arrowsize=11)
        style.configure('Horizontal.TScrollbar',background='#D7CCE9',troughcolor='#F8F6FC',borderwidth=0,arrowsize=11)
        style.map('Vertical.TScrollbar',background=[('active','#BFAADB')])
        style.map('Horizontal.TScrollbar',background=[('active','#BFAADB')])
        style.configure('Work.Horizontal.TProgressbar',background='#6351CE',troughcolor='#E5E8F4',borderwidth=0,lightcolor='#83B4F0',darkcolor='#3F5CE3')
        style.configure('Card.TCheckbutton',background='white',foreground=MUTED,font=(FONT,-12),padding=0)
        style.map('Card.TCheckbutton',background=[('active','white')])
        style.configure('Side.TCheckbutton',background=NAVY,foreground='#CAC0E4',font=(FONT,-12),padding=2)
        style.map('Side.TCheckbutton',background=[('active',NAVY)])
        self._checkbox_images=checkbox_images(self.root)
        style.element_create('Glass.Check.indicator','image',self._checkbox_images[0],('selected',self._checkbox_images[1]),border=0,sticky='')
        import copy
        checkbox_layout=copy.deepcopy(style.layout('TCheckbutton'))
        def replace_indicator(layout):
            for i,(name,options) in enumerate(layout):
                if name.endswith('.indicator'):layout[i]=('Glass.Check.indicator',options)
                if 'children' in options:replace_indicator(options['children'])
        replace_indicator(checkbox_layout)
        style.layout('Card.TCheckbutton',checkbox_layout);style.layout('Side.TCheckbutton',checkbox_layout)
        style.configure('Edit.TEntry',padding=(8,4),fieldbackground='#FAF8FF',bordercolor='#CBD4E8',lightcolor='#E2E8F5',foreground=INK)
        style.map('Edit.TEntry',bordercolor=[('focus','#5363CE')],lightcolor=[('focus','#91BDDD')])
        try:self.root.iconbitmap(str(Path(__file__).parent/'assets/app.ico'))
        except Exception:pass

        # A compact sidebar keeps batch settings away from the main action bar.
        side=tk.Frame(self.root,bg=NAVY,width=176);side.pack(side='left',fill='y');side.pack_propagate(False)
        brand=tk.Canvas(side,width=144,height=56,bg=NAVY,highlightthickness=0);brand.pack(pady=(20,4))
        rounded_rect(brand,2,5,44,47,10,fill=BLUE,outline='')
        brand.create_rectangle(12,14,34,36,outline='white',width=2)
        brand.create_text(23,25,text='号',fill='white',font=(FONT,-15,'bold'))
        brand.create_text(55,25,text='门牌识别',anchor='w',fill='white',font=(FONT,-19,'bold'))
        brand.create_line(55,44,103,44,fill='#58C5DE',width=2)
        brand.create_line(107,44,130,44,fill='#8191EB',width=1)
        brand.create_oval(134,42,138,46,fill='#58C5DE',outline='')
        self._label(side,'DOORPLATE WORKBENCH',10,'#BEC9DF').pack(anchor='w',padx=18,pady=(0,26))
        self._label(side,'工作空间',11,'#C5CEE2',True).pack(anchor='w',padx=20,pady=(0,10))
        self.nav_buttons={}
        for label in ['全部图片','待复核','已完成','失败']:
            b=ModernButton(side,label,lambda v=label:self.set_filter(v),width=144,height=40,
                           color=NAVY,foreground='#D4DDED',hover='#2B3A5A',surface=NAVY)
            b.pack(pady=3);self.nav_buttons[label]=b
        self._label(side,'识别设置',11,'#C5CEE2',True).pack(anchor='w',padx=20,pady=(25,10))
        ttk.Combobox(side,textvariable=self.mode,values=['门牌增强','基础 OCR'],state='readonly',width=12).pack(fill='x',padx=17,pady=(0,11))
        ttk.Checkbutton(side,text='包含子文件夹',variable=self.recursive,style='Side.TCheckbutton').pack(anchor='w',padx=17,pady=5)
        ttk.Checkbutton(side,text='导入后自动识别',variable=self.auto,style='Side.TCheckbutton').pack(anchor='w',padx=17,pady=5)
        bottom=tk.Frame(side,bg=NAVY);bottom.pack(side='bottom',fill='x',padx=16,pady=18)
        ModernButton(bottom,'使用帮助',self.show_help,width=144,height=34,color='#293955',hover='#354968',
                     foreground='#E3EAF8',surface=NAVY,border='#45617B').pack(pady=(0,14))
        self._label(bottom,'●  本地处理 · 图片无需上传',11,'#7BDBC8').pack(anchor='w')
        self._label(bottom,'桌面版  2.0',11,'#C5CEE2').pack(anchor='w',pady=(6,0))

        main=tk.Frame(self.root,bg=BG);main.pack(side='left',fill='both',expand=True)
        header=tk.Frame(main,bg=BG);header.pack(fill='x',padx=22,pady=(20,16))
        htext=tk.Frame(header,bg=BG);htext.pack(side='left')
        self._label(htext,'门牌识别工作台',26,INK,True).pack(anchor='w')
        self._label(htext,'从一张照片到整批门牌，让地址与数字清晰可查。',12,MUTED).pack(anchor='w',pady=(5,0))
        self.export_button=self._button(header,'导出结果',self.export,106,True);self.export_button.pack(side='right',padx=(8,0))
        self.clear_button=self._button(header,'清空列表',self.clear,98);self.clear_button.pack(side='right')

        stats=tk.Frame(main,bg=BG);stats.pack(fill='x',padx=22,pady=(0,15))
        self.stats_labels={};self.stat_tips=[];self._compact=None
        for i,(key,title,color,tip) in enumerate([
                ('total','图片总数',TEXT_BLUE,'支持文件夹批量导入'),('done','已完成',TEXT_TEAL,'含人工修正的记录'),
                ('review','待复核',TEXT_AMBER,'建议核对后再导出'),('failed','处理失败',TEXT_ROSE,'可查看原因并重试')]):
            stats.columnconfigure(i,weight=1)
            tint=['#EEF0FF','#EAFAF5','#FFF7E9','#FFF0F5'][i]
            accent=[BLUE,TEAL,'#E8A23A','#E46C87'][i]
            card=self._card(stats,fill=tint,accent=accent);card.grid(row=0,column=i,sticky='nsew',padx=(0,10 if i<3 else 0))
            cbody=tk.Frame(card,bg=tint);cbody.pack(fill='x',padx=16,pady=12)
            info=tk.Frame(cbody,bg=tint);info.pack(side='left')
            self._label(info,title,12,color,True).pack(anchor='w')
            tip_label=self._label(info,tip,12,NOTE);tip_label.pack(anchor='w',pady=(5,0));self.stat_tips.append(tip_label)
            value=self._label(cbody,'0',30,color,True);value.pack(side='right',padx=(5,0));self.stats_labels[key]=value

        action=self._card(main);action.pack(fill='x',padx=22,pady=(0,15))
        bar=tk.Frame(action,bg='white');bar.pack(fill='x',padx=12,pady=10)
        self.load_buttons=[]
        for label,command,width in [('＋ 导入图片',self.pick_files,110),('导入文件夹',self.pick_folder,108),('课程素材',self.course_files,88)]:
            b=self._button(bar,label,command,width);b.pack(side='left',padx=(0,7));self.load_buttons.append(b)
        self.cancel_button=self._button(bar,'取消任务',self.cancel,92,state='disabled');self.cancel_button.pack(side='right',padx=(7,0))
        self.start_button=self._button(bar,'开始识别  →',self.start,126,True);self.start_button.pack(side='right')

        footer=tk.Frame(main,bg=BG);footer.pack(side='bottom',fill='x',padx=22,pady=(10,14))
        self.progress=ttk.Progressbar(footer,mode='determinate',style='Work.Horizontal.TProgressbar');self.progress.pack(fill='x',pady=(0,8))
        self.status_label=tk.Label(footer,textvariable=self.status,bg=BG,fg=NOTE,font=(FONT,-12),anchor='w')
        self.status_label.pack(fill='x')

        body=ttk.Panedwindow(main,orient='horizontal');body.pack(fill='both',expand=True,padx=22,pady=(0,0))
        left=self._card(body,accent=BLUE);right=self._card(body,accent=PURPLE);body.add(left,weight=5);body.add(right,weight=6)
        preview_header=tk.Frame(left,bg='white');preview_header.pack(fill='x',padx=14,pady=(14,11))
        self._label(preview_header,'图片预览',15,INK,True).pack(side='left')
        ttk.Checkbutton(preview_header,text='显示文字框',variable=self.show_boxes,command=self.draw_preview,style='Card.TCheckbutton').pack(side='right')
        pfoot=tk.Frame(left,bg='white');pfoot.pack(side='bottom',fill='x',padx=12,pady=12)
        zoomrow=tk.Frame(pfoot,bg='white');zoomrow.pack(fill='x',pady=(0,10))
        for text,command,width in [('−',lambda:self.zoom(.8),32),('＋',lambda:self.zoom(1.25),32),('适应窗口',self.fit_preview,78),('100%',lambda:self.zoom_to(1.0),55)]:
            self._button(zoomrow,text,command,width,height=29).pack(side='left',padx=(0,4))
        self.zoom_label=self._label(zoomrow,'',12,MUTED);self.zoom_label.pack(side='right')
        self.file_label=self._label(pfoot,'支持 JPG / JPEG / PNG / BMP / WEBP',12,MUTED,anchor='w')
        self.file_label.pack(fill='x')
        self.dimension_label=self._label(pfoot,'可拖入图片或整个文件夹',12,NOTE,anchor='w');self.dimension_label.pack(fill='x',pady=(4,0))
        self.canvas=tk.Canvas(left,bg='#F1F5FB',highlightthickness=1,highlightbackground='#BED2E5',height=320,cursor='arrow')
        self.canvas.pack(fill='both',expand=True,padx=12)
        self.canvas.bind('<Configure>',lambda e:self.draw_preview())
        self.canvas.bind('<MouseWheel>',lambda e:self.zoom(1.15 if e.delta>0 else 1/1.15))
        self.canvas.bind('<ButtonPress-1>',self.pan_start);self.canvas.bind('<B1-Motion>',self.pan_move)
        self.canvas.bind('<Double-Button-1>',lambda e:self.fit_preview() if self.preview else self.pick_files())

        result_header=tk.Frame(right,bg='white');result_header.pack(fill='x',padx=14,pady=(14,10))
        self._label(result_header,'识别结果',15,INK,True).pack(side='left')
        self.visible_label=self._label(result_header,'0 条记录',12,MUTED);self.visible_label.pack(side='right')
        search=tk.Frame(right,bg='white');search.pack(fill='x',padx=12,pady=(0,10))
        self._label(search,'搜索',12,MUTED).pack(side='left',padx=(0,8))
        self.search_entry=ttk.Entry(search,textvariable=self.query,style='Edit.TEntry',width=14)
        self.search_entry.pack(side='left',fill='x',expand=True)
        ttk.Combobox(search,textvariable=self.filter_value,values=['全部图片','待复核','已完成','失败','待识别'],state='readonly',width=8).pack(side='left',padx=(8,0))
        self.query.trace_add('write',lambda *a:self.filter_rows());self.filter_value.trace_add('write',lambda *a:self.filter_rows())

        details=tk.Frame(right,bg='white');details.pack(side='bottom',fill='x',padx=14,pady=(6,8))
        tk.Frame(details,bg='#EBE3F6',height=1).pack(fill='x',pady=(0,6))
        detail_header=tk.Frame(details,bg='white');detail_header.pack(fill='x',pady=(0,5))
        self._label(detail_header,'结果详情 / 人工修正',13,INK,True).pack(side='left')
        self.selection_status=self._label(detail_header,'请选择图片',12,MUTED);self.selection_status.pack(side='right')
        fields=tk.Frame(details,bg='white');fields.pack(fill='x');fields.columnconfigure(0,weight=3);fields.columnconfigure(1,weight=2)
        self._label(fields,'地址 / 地名',12,MUTED).grid(row=0,column=0,sticky='w',pady=(0,2))
        self._label(fields,'门牌号',12,MUTED).grid(row=0,column=1,sticky='w',padx=(10,0),pady=(0,2))
        ttk.Entry(fields,textvariable=self.address,font=(FONT,-17),style='Edit.TEntry').grid(row=1,column=0,sticky='ew')
        ttk.Entry(fields,textvariable=self.number,font=(FONT,-19,'bold'),style='Edit.TEntry',width=7).grid(row=1,column=1,sticky='ew',padx=(10,0))
        self.save_button=self._button(fields,'保存修正',self.correct,86,height=38);self.save_button.grid(row=1,column=2,padx=(9,0))
        textframe=tk.Frame(details,bg='#F7F3FE');textframe.pack(fill='x',pady=(5,3))
        self.raw=tk.Text(textframe,height=3,font=(FONT,-12),bg='#F7F3FE',fg=NOTE,relief='flat',
                         highlightthickness=0,wrap='word',state='disabled',padx=9,pady=5)
        rawscroll=ttk.Scrollbar(textframe,orient='vertical',command=self.raw.yview);self.raw.configure(yscrollcommand=rawscroll.set)
        self.raw.pack(side='left',fill='both',expand=True);rawscroll.pack(side='right',fill='y')
        self._label(details,'得分仅供复核参考；修正后请导出保存。',12,NOTE).pack(anchor='w')

        table=tk.Frame(right,bg='white');table.pack(fill='both',expand=True,padx=12,pady=(0,0))
        table.rowconfigure(0,weight=1);table.columnconfigure(0,weight=1)
        self.tree=ttk.Treeview(table,columns=('file','address','number','score','status'),show='headings',selectmode='browse',height=5,style='Work.Treeview')
        for key,label,width in [('file','图片文件',134),('address','地址 / 地名',120),('number','门牌号',68),('score','得分',60),('status','状态',74)]:
            self.tree.heading(key,text=label);self.tree.column(key,width=width,minwidth=width,stretch=key in {'file','address'},anchor='w' if key in {'file','address'} else 'center')
        scroll=ttk.Scrollbar(table,orient='vertical',command=self.tree.yview)
        hscroll=ttk.Scrollbar(table,orient='horizontal',command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll.set,xscrollcommand=hscroll.set)
        self.tree.grid(row=0,column=0,sticky='nsew');scroll.grid(row=0,column=1,sticky='ns');hscroll.grid(row=1,column=0,sticky='ew')
        self.tree.tag_configure('review',foreground=TEXT_AMBER,background='#FFFAEE')
        self.tree.tag_configure('failed',foreground=TEXT_ROSE,background='#FFF2F6')
        self.tree.tag_configure('manual',foreground='#6540AC');self.tree.tag_configure('alt',background='#FBF8FF')
        self.tree.bind('<<TreeviewSelect>>',self.select)
        for widget in [self.root,self.canvas,self.tree]:
            widget.drop_target_register(DND_FILES);widget.dnd_bind('<<Drop>>',self.drop)
        self.root.bind('<Control-o>',lambda e:self.pick_files());self.root.bind('<Control-e>',lambda e:self.export())
        self.root.bind('<Control-f>',lambda e:self.search_entry.focus_set())
        self.root.bind('<Escape>',lambda e:self.cancel() if self.busy else None)
        self.root.bind('<Configure>',self._resize_workbench,add='+')
        self._refresh_stats();self.draw_preview()
        # Set a useful initial split after geometry has been measured.
        self.root.after(100,lambda:body.sashpos(0,int(body.winfo_width()*.43)) if body.winfo_exists() else None)

    def _resize_workbench(self,event):
        if event.widget is not self.root:return
        compact=event.height<800
        if compact==self._compact:return
        self._compact=compact;self.raw.configure(height=2 if compact else 3)
        for label in self.stat_tips:
            if compact:label.pack_forget()
            else:label.pack(anchor='w',pady=(5,0))

    def show_help(self):
        messagebox.showinfo('使用帮助','1. 拖入图片或文件夹，自动识别中文地址与数字门牌。\n2. 点击列表查看图片；滚轮缩放，按住鼠标拖动放大后的图片。\n3. 用搜索框查找文件名、地址或门牌号；侧栏可筛选待复核记录。\n4. 编辑地址和门牌号后点击“保存修正”，再导出 CSV 或 JSON。\n\n快捷键：Ctrl+O 导入图片 / Ctrl+F 搜索 / Ctrl+E 导出 / Esc 取消任务。\n\n识别完全在本机运行。低分、模糊或缺失内容仍需人工核对。')
    def _matches(self,r):
        query=self.query.get().strip().casefold();kind=self.filter_value.get()
        status=r['status']
        return (not query or query in ' '.join(str(r.get(k,'')) for k in ('filename','address','number','raw_text')).casefold()) and (
            kind=='全部图片' or status==kind or (kind=='已完成' and status in {'已完成','已修正'}))
    def _refresh_stats(self):
        if not hasattr(self,'stats_labels'):return
        counts={'total':len(self.records),'done':sum(r['status'] in {'已完成','已修正'} for r in self.records.values()),
                'review':sum(r['status']=='待复核' for r in self.records.values()),'failed':sum(r['status']=='失败' for r in self.records.values())}
        for key,label in self.stats_labels.items():label.configure(text=str(counts[key]))
        self.visible_label.configure(text=f'{len(self.tree.get_children())} / {len(self.records)} 条')
        for name,b in self.nav_buttons.items():
            active=name==self.filter_value.get();b.color=PRIMARY_GRADIENT[0] if active else NAVY
            b.gradient=PRIMARY_GRADIENT if active else None
            b.foreground='white' if active else '#D4DDED';b.redraw()
    def set_filter(self,value):self.filter_value.set(value)
    def filter_rows(self):
        if not hasattr(self,'tree'):return
        visible=[]
        for key,r in self.records.items():
            if self._matches(r):self.tree.move(key,'',len(visible));visible.append(key)
            else:self.tree.detach(key)
        if self.current not in visible:
            if visible:self.tree.selection_set(visible[0]);self.select()
            else:self._reset_selection()
        self._refresh_stats()
    def _update_row_visual(self,key):
        r=self.records[key]
        tag='manual' if r['corrected'] else ('failed' if r['status']=='失败' else ('review' if r['status']=='待复核' else 'alt' if list(self.records).index(key)%2 else ''))
        values=(r['filename'],r['address'],r['number'],f"{r['confidence']:.3f}" if r['tokens'] else '—',r['status'])
        if self.tree.exists(key):self.tree.item(key,values=values,tags=(tag,))
        else:self.tree.insert('','end',iid=key,values=values,tags=(tag,))
        if not self._matches(r):self.tree.detach(key)
        elif key not in self.tree.get_children():self.tree.move(key,'','end')
        self._refresh_stats()
    def _reset_selection(self):
        if hasattr(self,'tree'):self.tree.selection_remove(*self.tree.selection())
        self.current=None;self.preview=None;self.address.set('');self.number.set('')
        self.selection_status.configure(text='请选择图片',fg=MUTED)
        self.file_label.configure(text='支持 JPG / JPEG / PNG / BMP / WEBP')
        self.dimension_label.configure(text='可拖入图片或整个文件夹')
        self.raw.configure(state='normal');self.raw.delete('1.0','end');self.raw.configure(state='disabled');self.draw_preview()
    def select(self,event=None):
        selected=self.tree.selection()
        if not selected or selected[0] not in self.records:return
        key=selected[0];r=self.records[key];self.address.set(r['address']);self.number.set(r['number'])
        self.raw.configure(state='normal');self.raw.delete('1.0','end')
        text='原始文字：'+(r['raw_text'] or '尚未识别')+f"\n图像处理：{r['chosen']}    ·    耗时 {r['seconds']:.3f} 秒"
        if r['warnings']:text+='\n复核提示：'+'；'.join(r['warnings'])
        if r['error']:text+='\n失败原因：'+r['error']
        self.raw.insert('end',text);self.raw.configure(state='disabled')
        if key!=self.current:
            self.current=key;self.zoom_mode='fit';self.pan=[0,0]
            try:self.preview=Image.fromarray(cv2.cvtColor(read_image(r['path']),cv2.COLOR_BGR2RGB))
            except Exception:self.preview=None
        color=TEXT_AMBER if r['status']=='待复核' else TEXT_ROSE if r['status']=='失败' else TEXT_TEAL
        self.selection_status.configure(text=r['status'],fg=color)
        name=r['filename'];self.file_label.configure(text=name if len(name)<=39 else name[:22]+'…'+name[-13:])
        self.dimension_label.configure(text=f'{self.preview.width} × {self.preview.height} px    ·    {len(r["tokens"])} 个文字区域' if self.preview else '图片无法预览，请查看失败原因')
        self.draw_preview()
    def fit_preview(self):self.zoom_mode='fit';self.pan=[0,0];self.draw_preview()
    def zoom_to(self,value):
        if self.preview is None:return
        self.zoom_mode='custom';self.zoom_factor=max(.05,min(12,value));self.pan=[0,0];self.draw_preview()
    def zoom(self,factor):
        if self.preview is None:return
        scale=self._fit_scale() if self.zoom_mode=='fit' else self.zoom_factor
        self.zoom_mode='custom';self.zoom_factor=max(.05,min(12,scale*factor));self.draw_preview()
    def _fit_scale(self):return max(.01,min((self.canvas.winfo_width()-32)/self.preview.width,(self.canvas.winfo_height()-32)/self.preview.height))
    def pan_start(self,event):
        self._drag_origin=(event.x,event.y,self.pan[0],self.pan[1])
    def pan_move(self,event):
        if self.preview and self._drag_origin:
            x,y,px,py=self._drag_origin;self.pan=[px+event.x-x,py+event.y-y];self.draw_preview()
    def _draw_scan_edges(self,cw,ch):
        if min(cw,ch)<50:return
        for x,y,sx,sy in [(9,9,1,1),(cw-10,9,-1,1),(9,ch-10,1,-1),(cw-10,ch-10,-1,-1)]:
            self.canvas.create_line(x+sx*17,y,x,y,x,y+sy*17,fill=CYAN,width=2)
            self.canvas.create_line(x+sx*22,y,x+sx*27,y,fill='#8097C2',width=1)
    def draw_preview(self):
        if not hasattr(self,'canvas'):return
        self.canvas.delete('all');cw,ch=self.canvas.winfo_width(),self.canvas.winfo_height()
        if cw<=2 or ch<=2:return
        # A static scanner grid keeps photographs on a neutral inspection surface.
        for x in range(0,cw,24):self.canvas.create_line(x,0,x,ch,fill='#D8E6F2' if x%96==0 else '#E4EDF6')
        for y in range(0,ch,24):self.canvas.create_line(0,y,cw,y,fill='#D8E6F2' if y%96==0 else '#E4EDF6')
        if self.preview is None:
            self.zoom_label.configure(text='')
            cx,cy=cw/2,ch/2
            rounded_rect(self.canvas,cx-30,cy-76,cx+30,cy-16,16,fill='#E6EDFD',outline='#BCCDE6')
            self.canvas.create_rectangle(cx-13,cy-61,cx+13,cy-33,outline=BLUE,width=2)
            self.canvas.create_line(cx-8,cy-40,cx,cy-49,cx+8,cy-40,fill=BLUE,width=2)
            self.canvas.create_oval(cx+3,cy-57,cx+7,cy-53,fill=BLUE,outline='')
            failed=self.current and self.records.get(self.current,{}).get('status')=='失败'
            self.canvas.create_text(cx,cy+8,text='图片无法预览' if failed else '拖入图片或文件夹',fill=INK,font=(FONT,-19,'bold'))
            self.canvas.create_text(cx,cy+37,text='请在右侧查看失败原因' if failed else '中文地址与数字门牌，一次完成识别',fill=MUTED,font=(FONT,-12))
            self.canvas.create_text(cx,cy+66,text='或双击此处选择图片' if not failed else '',fill=TEXT_BLUE,font=(FONT,-12))
            self._draw_scan_edges(cw,ch)
            return
        scale=self._fit_scale() if self.zoom_mode=='fit' else self.zoom_factor
        iw,ih=self.preview.size;display_w,display_h=iw*scale,ih*scale
        # Only render the visible image region, so zooming large photos stays bounded.
        left=(cw-display_w)/2+self.pan[0];top=(ch-display_h)/2+self.pan[1]
        vx1,vy1=max(0,left),max(0,top);vx2,vy2=min(cw,left+display_w),min(ch,top+display_h)
        if vx2>vx1 and vy2>vy1:
            box=((vx1-left)/scale,(vy1-top)/scale,(vx2-left)/scale,(vy2-top)/scale)
            image=self.preview.transform((max(1,int(vx2-vx1)),max(1,int(vy2-vy1))),Image.Transform.EXTENT,box,Image.Resampling.BICUBIC)
            self.photo=ImageTk.PhotoImage(image);self.canvas.create_image(vx1,vy1,image=self.photo,anchor='nw')
        if self.show_boxes.get():
            for token in self.records.get(self.current,{}).get('tokens',[]):
                points=[coordinate for x,y in token['box'] for coordinate in (left+float(x)*scale,top+float(y)*scale)]
                self.canvas.create_line(*points,*points[:2],fill='#09B99E',width=2,joinstyle='round')
        self._draw_scan_edges(cw,ch)
        self.zoom_label.configure(text=f'{scale*100:.0f}%')
