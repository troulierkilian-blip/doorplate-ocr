"""Small native Tk controls used by the desktop workbench (no extra runtime)."""
import tkinter as tk
from PIL import Image, ImageDraw, ImageFilter, ImageTk

FONT = 'Microsoft YaHei UI'

def _rgb(color):
    return tuple(int(color[i:i+2],16) for i in (1,3,5))

def _mix(a,b,amount):
    return tuple(round(x+(y-x)*amount) for x,y in zip(a,b))

def _gradient(size,start,end):
    """Paint a small horizontal gradient, expanded without jagged edges."""
    w,h=size;a=_rgb(start);b=_rgb(end)
    line=Image.new('RGBA',(w,1))
    line.putdata([(*_mix(a,b,x/max(1,w-1)),255) for x in range(w)])
    return line.resize((w,h))

class RoundedCard(tk.Frame):
    """Rounded surface behind normal Tk children, preserving their geometry."""
    def __init__(self,master,surface='#F5F3FC',fill='white',accent=None,**kwargs):
        super().__init__(master,bg=surface,bd=0,highlightthickness=0,**kwargs)
        self.surface=surface;self.fill=fill;self.accent=accent
        self._size=None;self._pending=None;self._photo=None
        self._background=tk.Canvas(self,bg=surface,bd=0,highlightthickness=0)
        self._background.place(x=0,y=0,relwidth=1,relheight=1)
        self._background.bind('<Configure>',self._schedule)
    def _schedule(self,event=None):
        if self._pending:self.after_cancel(self._pending)
        self._pending=self.after(25,self._paint)
    def _paint(self):
        self._pending=None;w=self.winfo_width();h=self.winfo_height()
        if w<8 or h<8 or self._size==(w,h):return
        self._size=(w,h);s=2
        image=Image.new('RGBA',(w*s,h*s),self.surface)
        shadow=Image.new('RGBA',image.size);draw=ImageDraw.Draw(shadow)
        draw.rounded_rectangle((4*s,5*s,(w-3)*s,(h-2)*s),radius=16*s,fill=(77,55,143,24))
        shadow=shadow.filter(ImageFilter.GaussianBlur(3*s));image.alpha_composite(shadow)
        draw=ImageDraw.Draw(image)
        draw.rounded_rectangle((1*s,1*s,(w-2)*s,(h-5)*s),radius=15*s,
                               fill=self.fill,outline='#CDD8EB',width=s)
        draw.line((17*s,2*s,(w-17)*s,2*s),fill='#FFFFFF',width=s)
        if self.accent:
            draw.rounded_rectangle((7*s,14*s,10*s,max(16,h-17)*s),radius=2*s,fill=self.accent)
        if w>70 and h>35:
            draw.line(((w-31)*s,7*s,(w-12)*s,7*s,(w-12)*s,12*s),fill='#419CBB',width=s)
            draw.line((14*s,(h-9)*s,28*s,(h-9)*s),fill='#83ABC9',width=s)
            draw.ellipse(((w-39)*s,6*s,(w-36)*s,9*s),fill='#7296C8')
        self._photo=ImageTk.PhotoImage(image.resize((w,h),Image.Resampling.LANCZOS))
        self._background.delete('all');self._background.create_image(0,0,image=self._photo,anchor='nw')

def checkbox_images(master):
    """Crisp native-ttk indicators; the checkbox variables and events stay native."""
    images=[]
    for selected in [False,True]:
        s=3;im=Image.new('RGBA',(16*s,16*s));d=ImageDraw.Draw(im)
        d.rounded_rectangle((s,s,15*s,15*s),radius=4*s,
                            fill='#7561E9' if selected else '#FAF9FF',
                            outline='#7561E9' if selected else '#B8ACD7',width=s)
        if selected:d.line([(4*s,8*s),(7*s,11*s),(12*s,5*s)],fill='white',width=2*s,joint='curve')
        images.append(ImageTk.PhotoImage(im.resize((16,16),Image.Resampling.LANCZOS),master=master))
    return images

def rounded_rect(canvas, x1, y1, x2, y2, radius=9, **kwargs):
    r = min(radius, (x2-x1)/2, (y2-y1)/2)
    points = [x1+r,y1,x2-r,y1,x2,y1,x2,y1+r,x2,y2-r,x2,y2,
              x2-r,y2,x1+r,y2,x1,y2,x1,y2-r,x1,y1+r,x1,y1]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)

class ModernButton(tk.Canvas):
    """Mouse and keyboard accessible button with consistent pixel sizing."""
    def __init__(self, master, text, command, width=106, height=38,
                 color='#4868F5', foreground='white', hover='#3D5CE7',
                 surface='white', border='', state='normal', gradient=None, **kwargs):
        self.text=text;self.command=command;self.color=color;self.foreground=foreground
        self.hover=hover;self.border=border;self._state=state;self._hover=False;self._focused=False
        self.gradient=gradient;self._paint_key=None;self._photo=None
        super().__init__(master,width=width,height=height,bg=surface,
                         highlightthickness=0,bd=0,takefocus=True,**kwargs)
        self.bind('<Configure>',lambda e:self.redraw())
        self.bind('<Enter>',lambda e:self._enter(True));self.bind('<Leave>',lambda e:self._enter(False))
        self.bind('<Button-1>',self._click);self.bind('<Return>',self._click);self.bind('<space>',self._click)
        self.bind('<FocusIn>',lambda e:self._focus(True));self.bind('<FocusOut>',lambda e:self._focus(False))
        self.redraw()
    def _enter(self,value):self._hover=value;self.redraw()
    def _focus(self,value):self._focused=value;self.redraw()
    def _click(self,event=None):
        if self._state!='disabled':
            self.focus_set();self.command()
        return 'break'
    def configure(self,cnf=None,**kwargs):
        if isinstance(cnf,dict):kwargs={**cnf,**kwargs};cnf=None
        if 'state' in kwargs:self._state=kwargs.pop('state')
        if 'text' in kwargs:self.text=kwargs.pop('text')
        result=super().configure(cnf,**kwargs) if cnf is not None or kwargs else None
        self.redraw();return result
    config=configure
    def redraw(self):
        self.delete('all');w=self.winfo_width();h=self.winfo_height()
        if w<=1:w=int(super().cget('width'))
        if h<=1:h=int(super().cget('height'))
        disabled=self._state=='disabled'
        fill='#ECE9F4' if disabled else (self.hover if self._hover else self.color)
        fg='#746C86' if disabled else self.foreground
        key=(w,h,fill,self.gradient,self.border,self._focused,disabled,self.cget('bg'),self._hover)
        if self._paint_key!=key:
            self._paint_key=key;s=3
            image=Image.new('RGBA',(w*s,h*s),self.cget('bg'))
            shadow=Image.new('RGBA',image.size);draw=ImageDraw.Draw(shadow)
            if self.gradient and not disabled:
                draw.rounded_rectangle((3*s,4*s,(w-3)*s,(h-1)*s),radius=11*s,fill=(90,58,186,45))
                image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(2*s)))
            mask=Image.new('L',image.size);d=ImageDraw.Draw(mask)
            rect=(s,s,(w-2)*s,(h-3)*s)
            d.rounded_rectangle(rect,radius=10*s,fill=255)
            if self.gradient and not disabled:
                start,end=self.gradient
                if self._hover:start=fill
                face=_gradient(image.size,start,end)
                shine=Image.new('RGBA',image.size);sd=ImageDraw.Draw(shine)
                for y in range(1,max(2,h//2)):
                    sd.line((0,y*s,w*s,y*s),fill=(255,255,255,int(30*(1-y/(h/2)))),width=s)
                face.alpha_composite(shine)
            else:face=Image.new('RGBA',image.size,fill)
            image.paste(face,(0,0),mask)
            draw=ImageDraw.Draw(image)
            outline=self.border if not disabled else '#E5DFEF'
            if outline:draw.rounded_rectangle(rect,radius=10*s,outline=outline,width=s)
            if self.gradient and not disabled:
                draw.line((12*s,2*s,(w-13)*s,2*s),fill=(255,255,255,95),width=s)
            if w>=80 and not disabled:
                draw.line(((w-13)*s,5*s,(w-7)*s,5*s,(w-7)*s,10*s),
                          fill='#A7DAEC' if self.gradient else '#91ACCC',width=s)
            if self._focused and not disabled:
                draw.rounded_rectangle((3*s,3*s,(w-4)*s,(h-5)*s),radius=8*s,outline='#86BDDC',width=s)
            self._photo=ImageTk.PhotoImage(image.resize((w,h),Image.Resampling.LANCZOS))
        self.create_image(0,0,image=self._photo,anchor='nw')
        self.create_text(w/2,h/2-1,text=self.text,fill=fg,font=(FONT,-14,'bold'))
        super().configure(cursor='arrow' if disabled else 'hand2')
