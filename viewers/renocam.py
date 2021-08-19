#!/usr/bin/env python

# -------------------------------------------- #
#    __                    ___                 #
#   /__\ ___ _ __   ___   / __\__ _ _ __ ___   #
#  / \/// _ \ '_ \ / _ \ / /  / _` | '_ ` _ \  #
# / _  \  __/ | | | (_) / /__| (_| | | | | | | #
# \/ \_/\___|_| |_|\___/\____/\__,_|_| |_| |_| #
#                                              #
# -------------------------------------------- #

import pygame, sys
from pygame.locals import *
import numpy as np
import matplotlib.cm as cm
import struct 
import os
from PIL import Image
import time
import math as m
import copy
import datetime as dt
from astropy.io import fits as pf
from pyMilk.interfacing.isio_shmlib import SHM as shm
#from xaosim.scexao_shmlib import shm

MILK_SHM_DIR = os.environ['MILK_SHM_DIR']
home = os.getenv('HOME')

hmsg = """JEAN's INSTRUCTIONS
-------------------

camera controls:
---------------
SPACE  : start/stop data stream
CTRL+b : take new darks

display controls:
----------------
d      : subtract dark for display
c      : display cross
m      : color/gray color-map
f      : display flux mismatch
v      : start/stop accumulating and averaging frames
r      : subtract a reference image
CTRL+r : save the reference
CTRL+s : start/stop logging images

mouse controls:
--------------
mouse      : display of the flux under the mouse pointer
 
ESC   : quit renocam

"""

args = sys.argv[1:]
zoom = 3    # zoom for the display (default is 3)
if args != []:
    if isinstance(int(args[0]),int):
        zoom = int(args[0])+1
        zoom = min(4,max(2,zoom))

# ------------------------------------------------------------------
#                access to shared memory structures
# ------------------------------------------------------------------
cam = shm("ocam2d", verbose=False)
bias_shm = shm('aol0_wfsdark')

# ------------------------------------------------------------------
#                       global variables
# ------------------------------------------------------------------

mycmap = cm.gray
(xsize, ysize) = (120,120)#cam.size[:cam.naxis]

# -----------------------
#   set up the window
# -----------------------
pygame.display.init()
pygame.font.init()

FPS = 10                        # frames per second setting
fpsClock = pygame.time.Clock()  # start the pygame clock!
XW, YW = xsize*zoom, (ysize+50)*zoom

screen = pygame.display.set_mode((XW, YW), 0, 32)
pygame.display.set_caption('OCAM camera display!')

#os.system("tmux new-session -d -s ocam2k") #start a tmux session for messsages

# ------------------------------------------------------------------
#             short hands for shared memory data access
# ------------------------------------------------------------------
def get_img_data(check=False):
    ''' ----------------------------------------
    Return the current image data content,
    formatted as a 2D numpy array.
    Reads from the already-opened shared memory
    data structure.
    ---------------------------------------- '''
    return(cam.get_data(check, True).astype(float))

# ------------------------------------------------------------------
#  another short hand to convert numpy array into image for display
# ------------------------------------------------------------------
def arr2im(arr, vmin=0., vmax=10000.0, pwr=1.0):
    
    arr2 = arr.astype('float')**pwr
    
    mmin,mmax = arr2.min(), arr2.max()
    arr2 -= mmin
    if mmin < mmax:
        arr2 /= (mmax-mmin)

    if zoom != 1:
        img = Image.fromarray(arr2)
        rimg = img.resize((zoom*ysize, zoom*xsize))
        rarr = np.asarray(rimg)
        test = mycmap(rarr)
    else:
        test = mycmap(arr2)
    return((255*test[:,:,:3]).astype('int'))

# ------------------------------------------------------------------
#              !!! now we are in business !!!!
# ------------------------------------------------------------------

WHITE = (255, 255, 255)
GREEN = (147, 181,  44) 
BLUE  = (  0,   0, 255)
RED1   = (255,   0,   0)
RED   = (246, 133, 101) #(185,  95, 196)
BLK   = (  0,   0,   0)
CYAN  = (0, 255, 255)

FGCOL = WHITE  # foreground color (text)
SACOL = RED1   # saturation color (text)
BGCOL = BLK    # background color
BTCOL = BLUE   # *button* color

background = pygame.Surface(screen.get_size())
background = background.convert()

# ----------------------------
#          labels
# ----------------------------
font1 = pygame.font.SysFont("default",   8*zoom)
font2 = pygame.font.SysFont("default",   5*zoom)
font3 = pygame.font.SysFont("monospace", 4*zoom)
font5 = pygame.font.SysFont("monospace", 4*zoom)
font5.set_bold(True)

path_cartoon = "/home/scexao/conf/renocam_aux/Reno%db.png" % (zoom,)
cartoon1 = pygame.image.load(path_cartoon).convert_alpha()

lbl = font1.render("OCAM camera viewer", True, WHITE, BGCOL)
rct = lbl.get_rect()
rct.center = (45*zoom, 125*zoom)
screen.blit(lbl, rct)

lbl2 = font1.render("Press [h] for help", True, WHITE, BGCOL)
rct2 = lbl2.get_rect()
rct2.center = (45*zoom, 132*zoom)
screen.blit(lbl2, rct2)

lbl3 = font2.render("No women, no kids. Let's clean that wavefront.", True, WHITE, BGCOL)
rct3 = lbl3.get_rect()
rct3.center = (45*zoom, 140*zoom)
screen.blit(lbl3, rct3)

imin, imax = 0, 0
msg = "(min,max) = (%5d,%5d)" % (imin, imax)
info = font3.render(msg, True, FGCOL, BGCOL)
rct_info  = info.get_rect()
rct_info.center = (45*zoom, 145*zoom)

xmou, ymou, fmou = 0, 0, 0
msg2 = " mouse = (%3d,%3d), flux = %5d" % (xmou, ymou, fmou)
info2 = font3.render(msg2, True, FGCOL, BGCOL)
rct_info2  = info2.get_rect()
rct_info2.center = (45*zoom, 150*zoom)

dinfo = font3.render("       ", True, FGCOL, BGCOL)
rct_dinfo  = dinfo.get_rect()
rct_dinfo.center = (45*zoom, 155*zoom)
screen.blit(dinfo, rct_dinfo)

dinfo2 = font3.render("                          ", True, FGCOL, BGCOL)
rct_dinfo2  = dinfo2.get_rect()
rct_dinfo2.center = (45*zoom, 160*zoom)
screen.blit(dinfo2, rct_dinfo2)

xws = xsize*zoom
yws = ysize*zoom

msgsave1 = "saving images"
msgsave2 = "  before I   "
msgsave3 = "  kill you   "
savem1 = font5.render(msgsave1, True, RED1)
savem2 = font5.render(msgsave2, True, RED1)
savem3 = font5.render(msgsave3, True, RED1)
rct_savem1 = savem1.get_rect()
rct_savem2 = savem2.get_rect()
rct_savem3 = savem3.get_rect()
h_savem2 = savem2.get_height()
h_savem3 = savem3.get_height()
rct_savem1.bottomright = (xws-10*zoom, yws-h_savem2-h_savem3)
rct_savem2.bottomright = (xws-10*zoom, yws-h_savem3)
rct_savem3.bottomright = (xws-10*zoom, yws)

cx = xsize/2.
cy = ysize/2.

imin, imax = 0, 0
surf_live = pygame.surface.Surface((xws, yws))

rect1 = surf_live.get_rect()
rect1.topleft = (0, 0)

rect2 = cartoon1.get_rect()
rect2.bottomright = XW, YW
screen.blit(cartoon1,  rect2)

plot_cross = False # flag for display of the hotspot
subt_bias  = False # flag for bias subtraction
subt_ref   = False # flag for ref subtraction
cont_acq   = False 
clr_scale  = False # flag for the display color scale
average    = False # flag for averaging
saveim     = False # flag to save images
flux_calc  = False # flag for flux mismatch

bias = np.zeros((ysize,xsize))
ref_im = np.zeros((ysize,xsize))

pygame.mouse.set_cursor(*pygame.cursors.broken_x)
pygame.display.update()

cnta = 0
timeexpt = []

# =======================================================
# =======================================================
while True: # the main game loop
    clicked = False

    mycmap = cm.gray
    if clr_scale:
        mycmap = cm.inferno
    
    # read image
    temp = get_img_data()
    #temp = np.squeeze(np.mean(temp, axis=0))
    isat = np.percentile(temp, 99.995)
    if subt_bias:
        temp -= bias
    if average == True:
        cnta += 1
        if cnta == 1:
            temp2 = copy.deepcopy(temp)
        else:
            temp2 *= float(cnta)/float(cnta+1)
            temp2 += temp/float(cnta+1)
    else:
        temp2 = copy.deepcopy(temp)
        cnta = 0
    if flux_calc == True:
        flux1 = np.sum(temp2[:60,:60])
        flux2 = np.sum(temp2[:60,60:])
        flux3 = np.sum(temp2[60:,:60])
        flux4 = np.sum(temp2[60:,60:])
        flux14 = flux1+flux4
        flux23 = flux2+flux3
        fluxtot = flux14+flux23
        diff14 = (flux4-flux1)/flux14
        diff23 = (flux3-flux2)/flux23
        diffx = (flux4+flux2-flux1-flux3)/fluxtot
        diffy = (flux3+flux4-flux2-flux1)/fluxtot
        diffr = m.sqrt(diffx**2+diffy**2)
        #print diff14, diff23, diffx, diffy
        diff14b = m.copysign(m.pow(abs(diff14),0.5)*30*zoom*m.sqrt(2),diff14)
        diff23b = m.copysign(m.pow(abs(diff23),0.5)*30*zoom*m.sqrt(2),diff23)
        diffxb = m.pow(abs(diffr),0.5)*30*zoom*m.sqrt(2)*diffx/diffr
        diffyb = m.pow(abs(diffy),0.5)*30*zoom*m.sqrt(2)*diffy/diffr

    imax = np.max(temp2)
    imin = np.percentile(temp2, 0.5)
    temp2b = temp2-imin
    temp2b *= temp2b>0
    if subt_ref:
        if subt_bias:
            myim = arr2im((temp2b-ref_im+bias).transpose())
        else:
            myim = arr2im((temp2b-ref_im).transpose())
    else:
        myim = arr2im(temp2b.transpose())
    pygame.surfarray.blit_array(surf_live, myim)
    screen.blit(surf_live, rect1)
    
    msg = "(min,max) = (%5d,%5d)" % (imin, imax)
    info = font3.render(msg, True, FGCOL, BGCOL)
    screen.blit(info, rct_info)

    # display mouse information
    [xmou, ymou] = pygame.mouse.get_pos()
    xim = xmou//zoom
    yim = ymou//zoom
    if (xim >= 0) and (xim < xsize) and (yim >= 0) and (yim < ysize):
        fim = temp2[yim, xim]
        msg2 = " mouse = (%3d,%3d), flux = %5d" % (xim, yim, fim)
        info2 = font3.render(msg2, True, FGCOL, BGCOL)
        screen.blit(info2, rct_info2)
    
    # display information
    if subt_bias:
        msg = " bias  "
    else:
        msg = "no-bias"
    dinfo = font3.render(msg, True, FGCOL, BGCOL)
    screen.blit(dinfo, rct_dinfo)

    if isat > 15000:
        msg = "     !!!SATURATION!!!     "
        dinfo2 = font3.render(msg, True, BGCOL, SACOL)
        screen.blit(dinfo2, rct_dinfo2)
    elif isat > 11000 and isat <=15000:
        msg = "     !!!NON-LINEAR!!!     "
        dinfo2 = font3.render(msg, True, SACOL, BGCOL)
        screen.blit(dinfo2, rct_dinfo2)
    else:
        msg = "                          "
        dinfo2 = font3.render(msg, True, SACOL, BGCOL)
        screen.blit(dinfo2, rct_dinfo2)

    # display the cross
    if plot_cross:
        pygame.draw.line(screen, RED, (0, yws/2), (xws, yws/2), 1)
        pygame.draw.line(screen, RED, (xws/2, 0), (xws/2, yws), 1)
    

    # display flux mismatch
    if flux_calc:
        pygame.draw.line(screen, CYAN, (xws/2,yws/2), (xws/2+diff14b,yws/2+diff14b), 2)
        pygame.draw.circle(screen, CYAN, (int(xws/2+diff14b),int(yws/2+diff14b)), 2*zoom, 2)
        pygame.draw.line(screen, CYAN, (xws/2,yws/2), (xws/2-diff23b,yws/2+diff23b), 2)
        pygame.draw.circle(screen, CYAN, (int(xws/2-diff23b),int(yws/2+diff23b)), 2*zoom, 2)
        pygame.draw.line(screen, RED1, (xws/2,yws/2), (xws/2+diffxb,yws/2+diffyb), 2)
        pygame.draw.circle(screen, RED1, (int(xws/2+diffxb),int(yws/2+diffyb)), 2*zoom, 2)
    # saving images
    tmuxon = os.popen('tmux ls |grep ocamlog | awk \'{print $2}\'').read()
    if tmuxon:
        saveim = True
    else:
        saveim = False
    if saveim:
        screen.blit(savem1, rct_savem1)
        screen.blit(savem2, rct_savem2)
        screen.blit(savem3, rct_savem3)
        rects = [rect1, rct_info, rct_info2, rct_dinfo, rct_dinfo2, rct_savem1, rct_savem2, rct_savem3]
    else:
        rects = [rect1, rct_info, rct_info2, rct_dinfo, rct_dinfo2]
    
    # =====================================
    for event in pygame.event.get():

        if event.type == QUIT:
            pygame.quit()

            # close shared memory access
            # --------------------------
            cam.close()          # global disp map
            bias_shm.close()
            print("Renocam has ended normally.")
            sys.exit()
        elif event.type == KEYDOWN:

            if event.key == K_ESCAPE:
                pygame.quit()
                # close shared memory access
                # --------------------------
                cam.close()          # global disp map
                print("Renocam has ended normally.")
                sys.exit()

            if event.key == K_c:
                plot_cross = not plot_cross

            if event.key == K_f:
                flux_calc = not flux_calc

            if event.key == K_m:
                clr_scale = not clr_scale
   
            if event.key == K_d:
                subt_bias = not subt_bias
                if subt_bias:
                    bname = home+"/conf/renocam_aux/bias.fits"
                    try:
                        # bias = pf.getdata(bname)
                        bias = bias_shm.get_data()
                    except:
                        bias = np.zeros_like(temp)
                    
            if event.key == K_h:
                mmods = pygame.key.get_mods()
                print(hmsg)

            # secret chuck mode to re-acquire biases for all exp times
            # --------------------------------------------------------
            if event.key == K_b:
                mmods = pygame.key.get_mods()
                if (mmods & KMOD_LCTRL):
                    msg = "  !! Acquiring darks !!   "
                    dinfo2 = font3.render(msg, True, BGCOL, SACOL)
                    screen.blit(dinfo2, rct_dinfo2)
                    pygame.display.update([rct_dinfo2])
                    #os.system("log Chuckcam: Saving internal darks")
                    
                    
                    print("You want to be a cleaner?")
                    print("acquire all biases first.")
                    
                    subt_bias = False
                    
                    ndark = 1000
                    for idark in range(ndark):
                        if idark == 0:
                            temp3 = get_img_data(True)/float(ndark)
                        else:
                            temp3 += get_img_data(True)/float(ndark)
                            
                    bname = home+"/conf/renocam_aux/bias.fits"
                    
                    pf.writeto(bname, temp3, clobber=True)
                    time.sleep(0.2)
                    
            # Reno mode to save and subtract a reference image
            # --------------------------------------------------------
            if event.key == K_r:
                mmods = pygame.key.get_mods()
                if (mmods & KMOD_LCTRL):
                    msg = "!! Acquiring reference !! "
                    dinfo2 = font3.render(msg, True, BGCOL, SACOL)
                    screen.blit(dinfo2, rct_dinfo2)
                    pygame.display.update([rct_dinfo2])
 
                    subt_ref = False
                    
                    nref = 1000
                    for iref in range(nref):
                        if iref == 0:
                            temp3 = get_img_data(True)/float(nref)
                        else:
                            temp3 += get_img_data(True)/float(nref)
                                
                    rname = home+"/conf/renocam_aux/ref.fits"
                    pf.writeto(rname, temp3, clobber=True)
                    
                else:
                    rname = home+"/conf/renocam_aux/ref.fits"
                    ref_im = pf.getdata(rname)
                    subt_ref = not subt_ref

            if event.key == K_v:
                average = not average

            if event.key == K_s:
                mmods = pygame.key.get_mods()
                if (mmods & KMOD_LCTRL):
                    saveim = not saveim
                    if saveim:
                        timestamp = dt.datetime.utcnow().strftime('%Y%m%d')
                        savepath = '/media/data/'+timestamp+'/ocam2k/'
                        ospath = os.path.dirname(savepath)
                        if not os.path.exists(ospath):
                            os.makedirs(ospath)
                        nimsave = 10000
                        # creating a tmux session for logging
                        os.system("tmux new-session -d -s ocamlog")
                        os.system("tmux send-keys -t ocamlog \"logshim ocam2d %i %s\" C-m"%(nimsave, savepath))
                        #os.system("log Chuckcam: start logging images")
                    else:
                        os.system("tmux send-keys -t ocamlog \"logshimkill ircam1\"")
                        os.system("tmux kill-session -t ocamlog")
                        #os.system("log Chuckcam: stop logging images")

    pygame.display.update(rects)

    #pygame.display.flip()
    fpsClock.tick(FPS)

pygame.quit()
sys.exit()
