import numpy as np
import time
import centroid
import sys
from PyQt5.QtCore import (QThread, QTimer, pyqtSignal, Qt, QPoint, QLine,
                          QMutex, QObject, pyqtSlot)

from PyQt5.QtWidgets import (QApplication, QPushButton, QWidget,
                             QHBoxLayout, QVBoxLayout, QGraphicsScene,
                             QLabel,QGridLayout, QCheckBox, QFrame, QGroupBox,
                             QSpinBox,QDoubleSpinBox,QSizePolicy,QFileDialog,
                             QErrorMessage, QSlider)
from PyQt5.QtGui import QColor, QImage, QPainter, QPixmap, qRgb, QPen, QBitmap, QPalette, QIcon
import os
from matplotlib import pyplot as plt
import datetime
from tools import error_message, now_string, prepend, colortable, get_ram, get_process
import copy
from zernike import Reconstructor
import cProfile
import scipy.io as sio
from poke_analysis import save_modes_chart
from ctypes import CDLL,c_void_p
from search_boxes import SearchBoxes
from reference_generator import ReferenceGenerator
from ciao import config as ccfg
from frame_timer import FrameTimer
from poke import Poke
import os

sensor_mutex = QMutex()
mirror_mutex = QMutex()

try:
    os.mkdir('.gui_settings')
except Exception as e:
    print e

class ImageDisplay(QWidget):
    def __init__(self,name,downsample=1,clim=None,colormap=None,mouse_event_handler=None,image_min=None,image_max=None,width=512,height=512,zoom_height=ccfg.zoom_height,zoom_width=ccfg.zoom_width,zoomable=False,draw_boxes=False,draw_lines=False):
        super(ImageDisplay,self).__init__()
        self.name = name
        self.autoscale = False
        self.sx = width
        self.sy = height
        self.draw_boxes = draw_boxes
        self.draw_lines = draw_lines
        self.zoomable = zoomable
        
        if clim is None:
            try:
                clim = np.loadtxt('.gui_settings/clim_%s.txt'%name)
            except Exception as e:
                self.autoscale = True
        
        self.clim = clim
        self.pixmap = QPixmap()
        self.label = QLabel()
        self.image_max = image_max
        self.image_min = image_min
        self.zoom_width = zoom_width
        self.zoom_height = zoom_height
        
        layout = QHBoxLayout()
        layout.addWidget(self.label)

        if image_min is not None and image_max is not None and not self.autoscale:
            self.n_steps = 100
        
            self.cmin_slider = QSlider(Qt.Vertical)
            self.cmax_slider = QSlider(Qt.Vertical)

            self.cmin_slider.setMinimum(0)
            self.cmax_slider.setMinimum(0)

            self.cmin_slider.setSingleStep(1)
            self.cmax_slider.setSingleStep(1)

            self.cmin_slider.setPageStep(10)
            self.cmax_slider.setPageStep(10)

            self.cmin_slider.setMaximum(self.n_steps)
            self.cmax_slider.setMaximum(self.n_steps)

            self.cmin_slider.setValue(self.real2slider(self.clim[0]))
            self.cmax_slider.setValue(self.real2slider(self.clim[1]))

            self.cmin_slider.valueChanged.connect(self.set_cmin)
            self.cmax_slider.valueChanged.connect(self.set_cmax)
            
            layout.addWidget(self.cmin_slider)
            layout.addWidget(self.cmax_slider)

        
        self.setLayout(layout)
        
        self.zoomed = False
        self.colormap = colormap
        if self.colormap is not None:
            self.colortable = colortable(self.colormap)
        if mouse_event_handler is not None:
            self.mousePressEvent = mouse_event_handler
        else:
            self.mousePressEvent = self.zoom
            
        self.downsample = downsample
        
        data = np.random.rand(100,100)
        self.show(data)
        
        self.zoom_x1 = 0
        self.zoom_x2 = self.sx-1
        self.zoom_y1 = 0
        self.zoom_y2 = self.sy-1



        
    def real2slider(self,val):
        # convert a real value into a slider value
        return round(int((val-float(self.image_min))/float(self.image_max-self.image_min)*self.n_steps))

    def slider2real(self,val):
        # convert a slider integer into a real value
        return float(val)/float(self.n_steps)*(self.image_max-self.image_min)+self.image_min
    
    def set_cmax(self,slider_value):
        self.clim = (self.clim[0],self.slider2real(slider_value))
        np.savetxt('.gui_settings/clim_%s.txt'%self.name,self.clim)

    def set_cmin(self,slider_value):
        self.clim = (self.slider2real(slider_value),self.clim[1])
        np.savetxt('.gui_settings/clim_%s.txt'%self.name,self.clim)
        
    def show(self,data,boxes=None,lines=None,mask=None):

        if mask is None:
            if boxes is not None:
                mask = np.ones(boxes[0].shape)
            elif lines is not None:
                mask = np.ones(lines[0].shape)
            else:
                assert (boxes is None) and (mask is None)
        
#        if self.name=='mirror':
#            print data[6,6]
            
        if self.autoscale:
            clim = (data.min(),data.max())
        else:
            clim = self.clim

        cmin,cmax = clim
        downsample = self.downsample
        data = data[::downsample,::downsample]
        
        if self.zoomed:
            x_scale = float(data.shape[1])/float(self.sx)
            y_scale = float(data.shape[0])/float(self.sy)

            zy1 = int(round(self.zoom_y1*y_scale))
            zy2 = int(round(self.zoom_y2*y_scale))
            zx1 = int(round(self.zoom_x1*x_scale))
            zx2 = int(round(self.zoom_x2*x_scale))
            
            #data = data[self.zoom_y1:self.zoom_y2,self.zoom_x1:self.zoom_x2]
            data = data[zy1:zy2,zx1:zx2]
            
        bmp = np.round(np.clip((data.astype(np.float)-cmin)/(cmax-cmin),0,1)*255).astype(np.uint8)
        sy,sx = bmp.shape
        n_bytes = bmp.nbytes
        bytes_per_line = int(n_bytes/sy)
        image = QImage(bmp,sy,sx,bytes_per_line,QImage.Format_Indexed8)
        if self.colormap is not None:
            image.setColorTable(self.colortable)
        self.pixmap.convertFromImage(image)

        if boxes is not None and self.draw_boxes:
            x1vec,x2vec,y1vec,y2vec = boxes
            pen = QPen()
            pen.setColor(QColor(*ccfg.active_search_box_color))
            pen.setWidth(ccfg.search_box_thickness)
            painter = QPainter()
            painter.begin(self.pixmap)
            painter.setPen(pen)
            for index,(x1,y1,x2,y2) in enumerate(zip(x1vec,y1vec,x2vec,y2vec)):
                if mask[index]:
                    width = float(x2 - x1 + 1)/float(self.downsample)
                    painter.drawRect(x1/float(self.downsample)-self.zoom_x1,y1/float(self.downsample)-self.zoom_y1,width,width)
            painter.end()
            
        if lines is not None and self.draw_lines:
            x1vec,x2vec,y1vec,y2vec = lines
            pen = QPen()
            pen.setColor(QColor(*ccfg.slope_line_color))
            pen.setWidth(ccfg.slope_line_thickness)
            painter = QPainter()
            painter.begin(self.pixmap)
            painter.setPen(pen)
            for index,(x1,y1,x2,y2) in enumerate(zip(x1vec,y1vec,x2vec,y2vec)):
                if mask[index]:
                    painter.drawLine(QLine(x1/float(self.downsample)- self.zoom_x1,y1/float(self.downsample)-self.zoom_y1,x2/float(self.downsample)- self.zoom_x1,y2/float(self.downsample)- self.zoom_y1))
            painter.end()

        if sy==self.sy and sx==self.sx:
            self.label.setPixmap(self.pixmap)
        else:
            self.label.setPixmap(self.pixmap.scaled(self.sy,self.sx))
        
    def set_clim(self,clim):
        self.clim = clim

    def zoom(self,event):
        if not self.zoomable:
            return
        
        if self.zoom_width>=self.sx or self.zoom_height>=self.sy:
            return
        
        x,y = event.x(),event.y()
        
        if self.zoomed:
            self.zoomed = False
            self.zoom_x1 = 0
            self.zoom_x2 = self.sx-1
            self.zoom_y1 = 0
            self.zoom_y2 = self.sy-1
        else:
            self.zoomed = True
            self.zoom_x1 = x-self.zoom_width//2
            self.zoom_x2 = x+self.zoom_width//2
            self.zoom_y1 = y-self.zoom_height//2
            self.zoom_y2 = y+self.zoom_height//2
            if self.zoom_x1<0:
                dx = -self.zoom_x1
                self.zoom_x1+=dx
                self.zoom_x2+=dx
            if self.zoom_x2>self.sx-1:
                dx = self.zoom_x2-(self.sx-1)
                self.zoom_x1-=dx
                self.zoom_x2-=dx
            if self.zoom_y1<0:
                dy = -self.zoom_y1
                self.zoom_y1+=dy
                self.zoom_y2+=dy
            if self.zoom_y2>self.sy-1:
                dy = self.zoom_y2-(self.sy-1)
                self.zoom_y1-=dy
                self.zoom_y2-=dy
            #print 'zooming to %d,%d,%d,%d'%(self.zoom_x1,self.zoom_x2,self.zoom_y1,self.zoom_y2)

    def set_draw_lines(self,val):
        self.draw_lines = val

    def set_draw_boxes(self,val):
        self.draw_boxes = val
        
class UI(QWidget):

    def __init__(self,loop):
        super(UI,self).__init__()
        self.loop = loop
        self.loop.finished.connect(self.update)
        self.init_UI()
        self.frame_timer = FrameTimer('UI',verbose=False)
        self.show()

    def init_UI(self):
        self.setWindowIcon(QIcon('./icons/kungpao.png'))
        self.setWindowTitle('kungpao')
        layout = QHBoxLayout()
        imax = 2**ccfg.bit_depth-1
        imin = 0
        self.id_spots = ImageDisplay('spots',downsample=2,clim=None,colormap=ccfg.spots_colormap,image_min=imin,image_max=imax,draw_boxes=ccfg.show_search_boxes,draw_lines=ccfg.show_slope_lines,zoomable=True)
        #self.id_spots = ImageDisplay('spots',downsample=2,clim=(50,1000),colormap=ccfg.spots_colormap,image_min=imin,image_max=imax,draw_boxes=ccfg.show_search_boxes,draw_lines=ccfg.show_slope_lines,zoomable=True)
        layout.addWidget(self.id_spots)

        self.id_mirror = ImageDisplay('mirror',downsample=1,clim=(-0.5,0.5),colormap=ccfg.mirror_colormap,image_min=ccfg.mirror_command_min,image_max=ccfg.mirror_command_max,width=256,height=256)
        beam_d = ccfg.beam_diameter_m
        errmax = beam_d*1e-4
        self.id_wavefront = ImageDisplay('wavefront',downsample=1,clim=(-1.0e-8,1.0e-8),colormap=ccfg.wavefront_colormap,image_min=-errmax,image_max=errmax,width=256,height=256)

        
        column_1 = QVBoxLayout()
        column_1.setAlignment(Qt.AlignTop)
        column_1.addWidget(self.id_mirror)
        column_1.addWidget(self.id_wavefront)
        layout.addLayout(column_1)

        column_2 = QVBoxLayout()
        column_2.setAlignment(Qt.AlignTop)
        self.cb_closed = QCheckBox('Loop &closed')
        self.cb_closed.setChecked(self.loop.closed)
        self.cb_closed.stateChanged.connect(self.loop.set_closed)

        self.cb_draw_boxes = QCheckBox('Draw boxes')
        self.cb_draw_boxes.setChecked(self.id_spots.draw_boxes)
        self.cb_draw_boxes.stateChanged.connect(self.id_spots.set_draw_boxes)

        self.cb_draw_lines = QCheckBox('Draw lines')
        self.cb_draw_lines.setChecked(self.id_spots.draw_lines)
        self.cb_draw_lines.stateChanged.connect(self.id_spots.set_draw_lines)

        self.cb_logging = QCheckBox('Logging')
        self.cb_logging.setChecked(False)
        self.cb_logging.stateChanged.connect(self.loop.sensor.set_logging)
        self.cb_logging.stateChanged.connect(self.loop.mirror.set_logging)
        
        self.pb_poke = QPushButton('Poke')
        self.pb_poke.clicked.connect(self.loop.run_poke)
        self.pb_record_reference = QPushButton('Record reference')
        self.pb_record_reference.clicked.connect(self.loop.sensor.record_reference)
        self.pb_flatten = QPushButton('&Flatten')
        self.pb_flatten.clicked.connect(self.loop.mirror.flatten)
        self.pb_quit = QPushButton('&Quit')
        self.pb_quit.clicked.connect(sys.exit)

        poke_layout = QHBoxLayout()
        poke_layout.addWidget(QLabel('Modes:'))
        self.modes_spinbox = QSpinBox()
        self.modes_spinbox.setMaximum(ccfg.mirror_n_actuators)
        self.modes_spinbox.setMinimum(0)
        self.modes_spinbox.valueChanged.connect(self.loop.set_n_modes)
        self.modes_spinbox.setValue(self.loop.get_n_modes())
        poke_layout.addWidget(self.modes_spinbox)
        self.pb_invert = QPushButton('Invert')
        self.pb_invert.clicked.connect(self.loop.invert)
        poke_layout.addWidget(self.pb_invert)

        bg_layout = QHBoxLayout()
        bg_layout.addWidget(QLabel('Background correction:'))
        self.bg_spinbox = QSpinBox()
        self.bg_spinbox.setValue(self.loop.sensor.background_correction)
        self.bg_spinbox.setMaximum(500)
        self.bg_spinbox.setMinimum(-500)
        self.bg_spinbox.valueChanged.connect(self.loop.sensor.set_background_correction)
        bg_layout.addWidget(self.bg_spinbox)


        f_layout = QHBoxLayout()
        f_layout.addWidget(QLabel('Defocus:'))
        self.f_spinbox = QDoubleSpinBox()
        self.f_spinbox.setValue(0.0)
        self.f_spinbox.setSingleStep(0.01)
        self.f_spinbox.setMaximum(1.0)
        self.f_spinbox.setMinimum(-1.0)
        self.f_spinbox.valueChanged.connect(self.loop.sensor.set_defocus)
        f_layout.addWidget(self.f_spinbox)
        
        self.lbl_error = QLabel()
        self.lbl_error.setAlignment(Qt.AlignRight)
        self.lbl_tip = QLabel()
        self.lbl_tip.setAlignment(Qt.AlignRight)
        self.lbl_tilt = QLabel()
        self.lbl_tilt.setAlignment(Qt.AlignRight)
        self.lbl_cond = QLabel()
        self.lbl_cond.setAlignment(Qt.AlignRight)
        self.lbl_sensor_fps = QLabel()
        self.lbl_sensor_fps.setAlignment(Qt.AlignRight)
        self.lbl_mirror_fps = QLabel()
        self.lbl_mirror_fps.setAlignment(Qt.AlignRight)
        self.lbl_ui_fps = QLabel()
        self.lbl_ui_fps.setAlignment(Qt.AlignRight)
        
        column_2.addWidget(self.pb_flatten)
        column_2.addWidget(self.cb_closed)
        column_2.addLayout(f_layout)
        column_2.addLayout(bg_layout)
        column_2.addLayout(poke_layout)
        column_2.addWidget(self.cb_draw_boxes)
        column_2.addWidget(self.cb_draw_lines)
        column_2.addWidget(self.pb_quit)
        
        column_2.addWidget(self.lbl_error)
        column_2.addWidget(self.lbl_tip)
        column_2.addWidget(self.lbl_tilt)
        column_2.addWidget(self.lbl_cond)
        column_2.addWidget(self.lbl_sensor_fps)
        column_2.addWidget(self.lbl_mirror_fps)
        column_2.addWidget(self.lbl_ui_fps)
        
        column_2.addWidget(self.pb_poke)
        column_2.addWidget(self.pb_record_reference)
        column_2.addWidget(self.cb_logging)
        
        layout.addLayout(column_2)
        
        self.setLayout(layout)
        

    @pyqtSlot()
    def update(self):
        
        try:
            sensor = self.loop.sensor
            mirror = self.loop.mirror

            sb = sensor.search_boxes

            if self.id_spots.draw_boxes:
                boxes = [sb.x1,sb.x2,sb.y1,sb.y2]
            else:
                boxes = None

            if self.id_spots.draw_lines:
                lines = [sb.x,sb.x+sensor.x_slopes*ccfg.slope_line_magnification,
                         sb.y,sb.y+sensor.y_slopes*ccfg.slope_line_magnification]
            else:
                lines = None
                
            self.id_spots.show(sensor.image,boxes=boxes,lines=lines,mask=self.loop.active_lenslets)

            mirror_map = np.zeros(mirror.mask.shape)
            mirror_map[np.where(mirror.mask)] = mirror.get_command()[:]
            self.id_mirror.show(mirror_map)

            self.id_wavefront.show(sensor.wavefront)
            
            self.lbl_error.setText(ccfg.wavefront_error_fmt%(sensor.error*1e9))
            self.lbl_tip.setText(ccfg.tip_fmt%(sensor.tip*1000000))
            self.lbl_tilt.setText(ccfg.tilt_fmt%(sensor.tilt*1000000))
            self.lbl_cond.setText(ccfg.cond_fmt%(self.loop.get_condition_number()))
            self.lbl_sensor_fps.setText(ccfg.sensor_fps_fmt%sensor.frame_timer.fps)
            self.lbl_mirror_fps.setText(ccfg.mirror_fps_fmt%mirror.frame_timer.fps)
            self.lbl_ui_fps.setText(ccfg.ui_fps_fmt%self.frame_timer.fps)
        except Exception as e:
            print e
            
    def select_single_spot(self,click):
        print 'foo'
        x = click.x()*self.downsample
        y = click.y()*self.downsample
        self.single_spot_index = self.loop.sensor.search_boxes.get_lenslet_index(x,y)

    def paintEvent(self,event):
        self.frame_timer.tick()
