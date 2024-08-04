from socket import inet_ntoa
import tkinter as tk
from tkinter import ttk, filedialog
from tkinter.simpledialog import askstring
from tkinter.messagebox import showinfo
from utils import UserData, User
import requests
from base64 import b64decode
from PIL import Image, ImageTk
import io
import sys
import uuid
import os
import datetime


def addUserObservation(userdata):
    global NUM_OBSERVATIONS
    global ROW
    global COL
    if (userdata.username in users.keys()):
        user = users[userdata.username]
        user.data.append(userdata)
        user.update_score(round(userdata.score, 2))
        users[userdata.username] = user
    else:
        data = [userdata]
        user = User(userdata.username, list(data))
        users[user.username] = user
        addUserToFilter()

    addToGrid(userdata)

def addToGrid(userdata):
    global NUM_OBSERVATIONS
    global ROW
    global COL
    # Grid Data
    lblUser = tk.Label(master=myframe, text="User: " + userdata.username).grid(row=ROW + 1, column=COL, pady=15)

    img = userdata.image
    lblimage = tk.Label(master=myframe, image=img)
    lblimage.image = img
    lblimage.bind("<Button-1>", lambda event, ud=userdata: expandImage(event, ud))
    lblimage.grid(row=ROW + 2, column=COL, padx=20)

    lblCaption = tk.Label(master=myframe, text="Observation: " + userdata.user_caption,
                          wraplength=300, justify=tk.CENTER).grid(row=ROW + 3, column=COL)
    lblGenCaption = tk.Label(master=myframe, text="Generated Caption: " + userdata.generated_caption,
                             wraplength=300, justify=tk.CENTER).grid(row=ROW + 4, column=COL)
    lblFeedback = tk.Label(master=myframe, text="Feedback: " + userdata.feedback,
                           wraplength=300, justify=tk.CENTER).grid(row=ROW + 5, column=COL)

    NUM_OBSERVATIONS += 1
    if COL == COLUMNS - 1:
        ROW += 10
        COL = 0
    else:
        COL += 1

    my_canvas.update_idletasks()
    my_canvas.config(scrollregion=myframe.bbox())
    window.update()

def clearFrame():
   for widgets in myframe.winfo_children():
      widgets.destroy()

def filterByStudent():
    student = selectedStudent.get()
    print("Filtering by ", student)
    clearFrame()
    for key in users.keys():
        user = users[key]
        data = user.data
        if student == "Show All" or user.username == student:
            for observation in data:
                addToGrid(observation)

def addUserToFilter():
    filterMenu.children["menu"].delete(0,"end")
    filterMenu.children["menu"].add_command(label = "Show All", command = lambda a = "Show All": selectedStudent.set(a))
    for name in users.keys():
        filterMenu.children["menu"].add_command(label = name, command = lambda a = name: selectedStudent.set(a))
    selectedStudent.set("Show All")

def extractImage(photo):
    photo = photo.resize(size=(300, 200))
    img = ImageTk.PhotoImage(photo)
    return img


def collectDataFromAPI():
    api_url = API_URL + "/getData"
    response = requests.get(api_url)
    if (response.status_code == 200 and response.json()['userdata'] != {}):
        data = response.json()['userdata']
        image = b64decode(data['image'])
        photo = Image.open(io.BytesIO(image))
        img = extractImage(photo)
        u = UserData(data['user'], photo, img, None, data['usercaption'],
                     data['caption'], data['feedback'], round(float(data['score']), 2))
        addUserObservation(u)
    response = requests.get(api_url)
    window.after(1000, collectDataFromAPI)


def exportToCSV():
    global DIR_PATH
    print("Exporting data to csv...")

    DIR_PATH = filedialog.askdirectory(initialdir="/", title="Select directory to export data to")
    image_Path = DIR_PATH + '/images_' + datetime.datetime.now().strftime("%b%d_%Y") + '/'
    if (not os.path.exists(image_Path)):
        os.makedirs(image_Path)
    with open(DIR_PATH + '/observationData_' + datetime.datetime.now().strftime("%b%d_%Y") + '.csv', 'w') as f:
        f.write("User, Image Filename, User Observation, Generated Caption, Feedback, Score\n")
        for key in users.keys():
            user = users[key]
            data = user.data
            for d in data:
                d.image_filename = image_Path + uuid.uuid4().hex + ".png"
                # print(key, users[key], d, d.image_filename)
                ImageTk.getimage(d.image).save(d.image_filename, "PNG")
                f.write("%s,%s,%s,%s,%s,%.2f\n" % (key, d.image_filename,
                        d.user_caption, d.generated_caption, d.feedback, d.score))


def expandImage(event, userdata):
    # print("Expanding observation by ", userdata.username)
    w = tk.Toplevel(window)
    w.title("Observation expanded...")

    lblUser = tk.Label(master=w, text="User: " + userdata.username,font=("Times", 20)).grid(row=0, column=0, pady=15)

    photo = userdata.photo.resize(size=(600, 400))
    img = ImageTk.PhotoImage(photo)

    lblimage = tk.Label(master=w, image=img)
    lblimage.image = img
    lblimage.grid(row=1, column=0, padx=20)

    lblCaption = tk.Label(master=w, text="Observation: " + userdata.user_caption, wraplength=600,
                          justify=tk.CENTER, font=("Times", 20)).grid(row=2, column=0)
    lblGenCaption = tk.Label(master=w, text="Generated Caption: " + userdata.generated_caption,
                             wraplength=600, justify=tk.CENTER, font=("Times", 20)).grid(row=3, column=0)
    lblFeedback = tk.Label(master=w, text="Feedback: " + userdata.feedback, wraplength=600,
                           justify=tk.CENTER, font=("Times", 20)).grid(row=4, column=0)
    w.grid_columnconfigure(0,weight=1)
    w.mainloop()


def run():
    collectDataFromAPI()
    window.mainloop()


DIR_PATH = None
COLUMNS = 4
NUM_OBSERVATIONS = 0
ROW = 0
COL = 0

argc = len(sys.argv)
if (argc <= 1):
    print("Please specify an api url!")
    print("Usage: python3 visualizer.py [API_URL]")
    sys.exit()
API_URL = sys.argv[1]

users = dict()
window = tk.Tk()
window.attributes('-fullscreen', True)
window.title("Feedback Board")
title = tk.Label(window, text="Feedback Board", font=("Times", 30, "bold")).pack()

btnExport = tk.Button(
    master=window,
    text="Export",
    font=("Times", 20),
    highlightbackground="gold4",
    bg="gold4",
    fg="black",
    command=lambda: exportToCSV(),
).pack(pady=20)

#Set the Menu initially
optionlist = ["Show All"]
selectedStudent= tk.StringVar()
selectedStudent.set("Show All")

#Create a dropdown Menu
filterMenu = tk.OptionMenu(window, selectedStudent,*optionlist)
filterMenu.pack()
filterButton = tk.Button(window , text = "Filter by username" , command = filterByStudent).pack()

main_frame = tk.Frame(window)
main_frame.pack(fill=tk.BOTH, expand=1)

my_canvas = tk.Canvas(main_frame)
my_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

my_scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=my_canvas.yview)
my_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

my_canvas.configure(yscrollcommand=my_scrollbar.set)

my_canvas.bind('<Configure>', lambda e: my_canvas.configure(scrollregion=my_canvas.bbox("all")))


def _on_mouse_wheel(event):
    my_canvas.yview_scroll(-1 * int((event.delta / 120)), "units")


my_canvas.bind_all("<MouseWheel>", _on_mouse_wheel)

myframe = tk.Frame(my_canvas, padx=30)

my_canvas.create_window((0, 0), window=myframe, anchor="nw")

run()
