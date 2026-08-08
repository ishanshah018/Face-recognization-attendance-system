# pyrefly: ignore [missing-import]
import cv2
import numpy as np
import sqlite3

faceDetect=cv2.CascadeClassifier('haarcascade_frontalface_default.xml') #to detect the faces in camera
cam=cv2.VideoCapture(0)  # 0 is for web camera

if not cam.isOpened():
    print("Error: Could not open camera. Please check camera connection and macOS Camera permissions under 'System Settings' -> 'Privacy & Security' -> 'Camera'.")
    exit()

def insertorupdate(Id, Name, age):
    conn = sqlite3.connect("database.db")
    cursor = conn.execute("SELECT * FROM STUDENTS WHERE Id=?", (Id,))
    isRecordExist = cursor.fetchone() is not None

    if isRecordExist:
        conn.execute("UPDATE STUDENTS SET Name=?, age=? WHERE Id=?", (Name, age, Id))
    else:
        conn.execute("INSERT INTO STUDENTS (Id, Name, age) VALUES (?, ?, ?)", (Id, Name, age))

    conn.commit()
    conn.close()

    
#Taking User Inputs

Id=input("Enter User Id: ")
Name=input("Enter User Name: ")
age=input("Enter User Age: ")

insertorupdate(Id,Name,age)

# detect face in web camera coding

sampleNum=0

while(True):
    ret,img=cam.read()
    if not ret or img is None:
        print("Error: Failed to read frame from camera.")
        break
    gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY) # Image convert into BGRGRAY Color
    faces=faceDetect.detectMultiScale(gray,1.3,5)  

    for(x,y,w,h) in faces:
        sampleNum=sampleNum+1  #if face is detected it increaments
        cv2.imwrite("dataset/user."+str(Id)+"."+str(sampleNum)+".jpg",gray[y:y+h,x:x+w])
        cv2.rectangle(img,(x,y),(x+w,y+h),(0,255,0),2)
        cv2.waitKey(100)  #delay time
    cv2.imshow("Face",img) #show faces detected in web camera
    cv2.waitKey(1)

    if(sampleNum>20):
        break

cam.release()
cv2.destroyAllWindows()