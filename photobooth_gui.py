'''
Open source photo booth.

Kevin Osborn and Justin Shaw
WyoLum.com
'''

## imports
from gpiozero import Button as gpioButton
from tkkb import Tkkb
import time
from Tkinter import *
import tkMessageBox
import ImageTk
from mailfile import *
import custom
import Image
import config
from constants import *
from email.utils import parseaddr
import urllib2


# a simple check to see if we have an internet connection and can reach google
is_online = False
signed_in = False
def check_internet_connecton():
    try:
        # use google's ip address to avoid a DNS lookup 172.217.3.174
        urllib2.urlopen('http://172.217.3.174', timeout=1)
        return True
    except:
        return False


## This is a simple GUI, so we allow the root singleton to do the legwork
root = Tk()
root.attributes("-fullscreen",True)

def screenshot(*args):
    import screenshot
    screenshot.snap()
root.bind('<F12>', screenshot)

### booth cam may need to present a file dialog gui.  So import after root is defined.
from boothcam import *

## set display geometry
WIDTH  = SCREEN_W # 800
HEIGHT = SCREEN_H # 480
albumID_informed = False ### only show albumID customize info once

## set photo size to fit nicely in screen
SCALE = 1.8

## the countdown starting value
# COUNTDOWN1 = custom.countdown1 ### use custom.countdown1 reference directly

## put the status widget below the displayed image
STATUS_H_OFFSET = int(SCREEN_H*0.3) # 150 ## was 210

## only accept button inputs from the AlaMode when ready
Button_enabled = False

import signal
TIMEOUT = .3 # number of seconds your want for timeout

last_snap = time.time()

tkkb = None
def launch_tkkb(*args):
    '''
    Launch on screen keyboard program called tkkb-keyboard.
    install with '$ sudo apt-get install tkkb-keyboard'
    '''
'''
    global tkkb
    if tkkb is None:
        tkkb = Toplevel(root)
        def onEnter(*args):
            kill_tkkb()
            sendPic()
        Tkkb(tkkb, etext, onEnter=onEnter)
        etext.config(state=NORMAL)
        tkkb.wm_attributes("-topmost", 1)
        tkkb.transient(root)
        tkkb_button.config(command=kill_tkkb, text="Close KB")
        tkkb.protocol("WM_DELETE_WINDOW", kill_tkkb)
'''
        
def kill_tkkb():
    '''
    Delete on screen keyboard program called tkkb-keyboard.
    '''
    global tkkb
    if tkkb is not None:
        tkkb.destroy()
        try:
            tkkb_button.config(command=launch_tkkb, text="Open KB")
            tkkb = None
        except:
            pass


def interrupted(signum, frame):
    "called when serial read times out"
    print 'interrupted!'
    signal.signal(signal.SIGALRM, interrupted)

def display_image(im=None):
    '''
    display image im in GUI window
    '''
    global image_tk
    
    x,y = im.size
    x = int(x / SCALE)
    y = int(y / SCALE)

#    im = im.resize((x,y));
    image_tk = ImageTk.PhotoImage(im)

    ## delete all canvas elements with "image" in the tag
    can.delete("image")
#    can.create_image([(WIDTH + x) / 2 - x/2, 0 + y / 2], image=image_tk, tags="image")
    can.create_image([int(CANVAS_W/2), int(CANVAS_H/2)], image=image_tk, tags="image")
#    can.create_image([IMAGE_W, IMAGE_H], image=image_tk, tags="image")

def timelapse_due():
    '''
    Return true if a time lapse photo is due to be taken (see custom.TIMELAPSE)
    '''
    if custom.TIMELAPSE > 0:
        togo = custom.TIMELAPSE - (time.time() - last_snap)
        timelapse_label.config(text=str(int(togo)))
        out = togo < 0
    else:
        out = False
    return out

def refresh_oauth2_credentials():
    if custom.SIGN_ME_IN:
        if setup_google():
            print 'refreshed!', custom.oauth2_refresh_period
        else:
            print 'refresh failed'
        root.after(custom.oauth2_refresh_period, refresh_oauth2_credentials)
    
def check_and_snap(force=False, countdown1=None):
    '''
    Check button status and snap a photo if button has been pressed.

    force -- take a snapshot regarless of button status
    countdown1 -- starting value for countdown timer
    '''
    global  image_tk, Button_enabled, last_snap, is_online, signed_in
    
    if countdown1 is None:
        countdown1 = custom.countdown1
    if is_online and signed_in:
        send_button.config(state=NORMAL)
        etext.config(state=NORMAL)
    else:
        send_button.config(state=DISABLED)
        etext.config(state=DISABLED)
    if (Button_enabled == False):
        ## inform alamode that we are ready to receive button press events
        ## ser.write('e') #enable button (not used)
        Button_enabled = True
        # can.delete("text")
        # can.create_text(CANVAS_W/2, CANVAS_H - STATUS_H_OFFSET, text="Press button when ready", font=custom.CANVAS_FONT, tags="text")
        # can.update()
        
    ## get command string from alamode
#    command = ser.readline().strip()
    command=""
    if Button_enabled and (force or command == "snap" or timelapse_due()):
        ## take a photo and display it
        Button_enabled = False
        can.delete("text")
        can.update()
        
        if timelapse_due():
            countdown1 = 0
        im = snap(can, countdown1=countdown1, effect='None')
#        setLights(r_var.get(), g_var.get(), b_var.get())
        if im is not None:
            if custom.TIMELAPSE > 0:
                togo = custom.TIMELAPSE - (time.time() - last_snap)
            else:
                togo = 1e8
            last_snap = time.time()
            display_image(im)
            if is_online:
                can.delete("text")
                can.create_text(CANVAS_W/2, CANVAS_H - STATUS_H_OFFSET, text="Uploading Image", font=custom.CANVAS_FONT, tags="text")
                can.update()
                if signed_in:
                    if custom.albumID == 'None':
                        global albumID_informed
                        if not albumID_informed:
                            tkMessageBox.showinfo(
                                'Album ID not set',
                                'Click [Setup] to select albumID',
                                parent=root
                            )
                            albumID_informed = True
                    else:
                        try:
                            googleUpload(custom.PROC_FILENAME)
                        except Exception, e:
                            tkMessageBox.showinfo("Upload Error", str(e) +
                                                  '\nUpload Failed:%s' % e)
                        
                        # signed_in = False
                can.delete("text")
                # can.create_text(CANVAS_W/2, CANVAS_H - STATUS_H_OFFSET, text="Press button when ready", font=custom.CANVAS_FONT, tags="text")
                can.update()
    else:
        ### what command did we get?
        if command.strip():
            print command
    if not force:
        ## call this function again in 100 ms
        root.after_id = root.after(100, check_and_snap)

## for clean shutdowns
root.after_id = None
def on_close(*args, **kw):
    '''
    when window closes cancel pending root.after() call
    '''
    if root.after_id is not None:
        root.after_cancel(root.after_id)

    ### turn off LEDs
    r_var.set(0)
    g_var.set(0)
    b_var.set(0)
    root.quit()
root.protocol('WM_DELETE_WINDOW', on_close)

def force_snap(countdown1=None):
    if countdown1 is None:
        countdown1 = custom.countdown1
    check_and_snap(force=True, countdown1=countdown1)



#if they enter an email address send photo. add error checking
def sendPic(*args):
    if is_online:
        if signed_in:
            mailto = email_addr.get().strip()
            if '@' in parseaddr( mailto )[1]:
                print 'sending photo by email to %s' % mailto
                can.delete("splash")
                can.create_text(CANVAS_W/2, CANVAS_H/2, text=("Email to %s" % mailto), font=custom.CANVAS_FONT, tags="splash")
                can.update()
                try:
                    sendMail(mailto,
                             custom.emailSubject,
                             custom.emailMsg,
                             custom.PROC_FILENAME)
                    etext.delete(0, END)
                    etext.focus_set()
                    kill_tkkb()
                    can.delete("splash")
                    can.create_text(CANVAS_W/2, CANVAS_H/2, text=("Sent to %s" % mailto), font=custom.CANVAS_FONT, tags="splash")
                    can.update()
                    sleep(2)
                    can.delete("splash")
                except Exception, e:
                    print 'Send Failed::', e
                    can.delete("all")
                    can.create_text(CANVAS_W/2, CANVAS_H - STATUS_H_OFFSET, text="Send Failed", font=custom.CANVAS_FONT, tags="text")
                    can.update()
                    time.sleep(1)
                    can.delete("all")
                    im = Image.open(custom.PROC_FILENAME)
                    display_image(im)
                    can.create_text(CANVAS_W/2, CANVAS_H - STATUS_H_OFFSET, text="Press button when ready", font=custom.CANVAS_FONT, tags="text")
                    can.update()
            else:
                can.delete("splash")
                can.create_text(CANVAS_W/2, CANVAS_H/2, text=("Type an Email address first"), font=custom.CANVAS_FONT, tags="splash")
                can.update()
                sleep(2)
                can.delete("splash")
        else:
            print 'Not signed in'
            can.delete("splash")
            can.create_text(CANVAS_W/2, CANVAS_H/2, text=("Not signed in"), font=custom.CANVAS_FONT, tags="splash")
            can.update()
            sleep(2)
            can.delete("splash")
    else:
        can.delete("splash")
        can.create_text(CANVAS_W/2, CANVAS_H/2, text=("Offline, cannot send email"), font=custom.CANVAS_FONT, tags="splash")
        can.update()
        sleep(2)
        can.delete("splash")

#ser = findser()

def delay_timelapse(*args):
    '''
    Prevent a timelapse snapshot when someone is typeing an email address
    '''
    global last_snap
    last_snap = time.time()

#bound to text box for email
email_addr = StringVar()
email_addr.trace('w', delay_timelapse)

## bound to RGB sliders
r_var = IntVar()
g_var = IntVar()
b_var = IntVar()

## send RGB changes to alamode
def on_rgb_change(*args):
    setLights(r_var.get(), g_var.get(), b_var.get())

## call on_rgb_change when any of the sliders move
r_var.trace('w', on_rgb_change)
g_var.trace('w', on_rgb_change)
b_var.trace('w', on_rgb_change)

w, h = root.winfo_screenwidth(), root.winfo_screenheight()

# root.overrideredirect(1)
#root.geometry("%dx%d+0+0" % (WIDTH*SCALE, HEIGHT*SCALE))
#root.geometry("%dx%d+%d+%d" % (w, h, -w, -h)) #, int((w - CANVAS_W)/2), int((h - CANVAS_H)/2)))
root.geometry("%dx%d+%d+%d" % (CANVAS_W, CANVAS_H, int(SCREEN_W - CANVAS_W), int(SCREEN_H - CANVAS_H)))
root.focus_set() # <-- move focus to this widget
frame = Frame(root)

# Button(frame, text="Exit", command=on_close).pack(side=LEFT)
setup_button = Button(frame, text="Setup", command=lambda *args: custom.customize(root))
# show Setup button
#setup_button.pack(side=LEFT)
tkkb_button = Button(frame, command=launch_tkkb, text="Launch-KB")
# tkkb_button.pack(side=LEFT)
send_button = Button(frame, text="SendEmail", command=sendPic, font=custom.BUTTON_FONT)
# show SendEmail button
#send_button.pack(side=RIGHT)

setup_btn = gpioButton(18)
setup_btn.when_pressed = lambda *args: custom.customize(root)

take_pic_btn = gpioButton(23)
take_pic_btn.when_pressed = force_snap

email_btn = gpioButton(24)
email_btn.when_pressed = sendPic

if custom.TIMELAPSE > 0:
    timelapse_label = Label(frame, text=custom.TIMELAPSE)
else:
    timelapse_label = Label(frame, text='')
timelapse_label.pack(side=LEFT)

## add a text entry box for email addresses
etext = Entry(frame,width=40, textvariable=email_addr, font=custom.BUTTON_FONT)
etext.pack()
frame.pack()
etext.bind('<Button-1>', launch_tkkb)

def labeled_slider(parent, label, from_, to, side, variable):
    frame = Frame(parent)
    Label(frame, text=label).pack(side=TOP)
    scale = Scale(frame, from_=from_, to=to, variable=variable, resolution=1).pack(side=TOP)
    frame.pack(side=side)
    return scale

## add a software button in case hardware button is not available
interface_frame = Frame(root)

snap_button = Button(interface_frame, text="snap", command=force_snap, font=custom.BUTTON_FONT)
# snap_button.pack(side=RIGHT) ## moved to canvas
interface_frame.pack(side=RIGHT)

## the canvas will display the images
can = Canvas(root, width=CANVAS_W, height=CANVAS_H)
#can = Canvas(root, bg='red', width=CANVAS_W, height=CANVAS_H)
can.pack()
def snap_callback(*args):
    force_snap()
can.bind('<Button-1>', snap_callback)

# verify internet_connection
is_online = check_internet_connecton()

if is_online:
    ## sign in to google?
    if custom.SIGN_ME_IN:
        signed_in = setup_google()
    else:
        signed_in = False

if not signed_in:
    send_button.config(state=DISABLED)
    etext.config(state=DISABLED)

### take the first photo (no delay)
can.delete("text")
can.create_text(CANVAS_W/2, CANVAS_H/2, text="SMILE ;-)", font=custom.CANVAS_FONT, tags="splash")
can.update()
force_snap(countdown1=0)

### check button after waiting for 200 ms
root.after(200, check_and_snap)
if custom.SIGN_ME_IN:
    root.after(custom.oauth2_refresh_period, refresh_oauth2_credentials)
root.wm_title("Family Fun Fotobooth")
etext.focus_set()
# etext.bind("<Enter>", sendPic)
on_rgb_change()
root.mainloop()


