import cv2
import numpy as np
from blend_modes import difference
import sys
import csv

hr = []

with open("VideoData.csv", 'r') as file:
  csvreader = csv.reader(file, delimiter=';')
  
  for row in csvreader:
    hr.append(row[2])
    

vidcap = cv2.VideoCapture(sys.path[0] + "/video.mov")
success,currentFrame = vidcap.read()
count = 0

fourcc = cv2.VideoWriter_fourcc(*"MP4V")
writer = cv2.VideoWriter(sys.path[0] + "/textvid.mov", fourcc, 60.0, (1080, 1920))

img_array = []
count = 0
hrUpdate = 0

while success:
  font = cv2.FONT_HERSHEY_SIMPLEX

  cv2.putText(currentFrame, hr[hrUpdate] + "<3", (250, 50), font, 3, (0, 0, 255), 2, cv2.LINE_4)

  writer.write(currentFrame)

  success,currentFrame = vidcap.read()
  print('Read a new frame: ', success)

  count += 1

  if count % 285 == 0:
    hrUpdate += 1

writer.release()