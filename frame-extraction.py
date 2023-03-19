import cv2
import numpy as np
from blend_modes import difference
import sys
import csv
import json
import datetime
import ffmpeg # Video Metadata

videoPath = sys.path[0] + "/video.mov"

jsonMetadata = ffmpeg.probe(videoPath)

workoutData = open(sys.path[0] + "/2023-03-17_07-12-24_hk_1679033544.rungap.json")

for i in jsonMetadata["streams"]:
  if i.get("index") == 0:
    vidW = i.get("width")
    vidH = i.get("height")
    vidFR = i.get("r_frame_rate")
    vidLen = i.get("duration")
    nested = i.get("tags")
    vidCreationT = nested.get("creation_time")
    usefulMeta = [vidW, vidH, vidFR, vidLen, vidCreationT]
  
hr = []

data = json.load(workoutData)

for i in data["laps"][0]["points"]:
    if i.get("hr"):
        hr.append(i.get("hr"))
        # print(i.get("time"))
        # print(datetime.datetime.fromtimestamp(i.get("time")))

vidcap = cv2.VideoCapture(videoPath)
success,currentFrame = vidcap.read()
count = 0


fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(sys.path[0] + "/textvid.mov", fourcc, 60.0, (usefulMeta[1], usefulMeta[0]))

img_array = []
count = 0
hrUpdate = 0

while success:
  font = cv2.FONT_HERSHEY_SIMPLEX

  cv2.putText(currentFrame, str(hr[hrUpdate]), (50, 250), font, 3, (0, 0, 255), 2, cv2.LINE_4)

  writer.write(currentFrame)

  success,currentFrame = vidcap.read()
  print('Read a new frame: ', success)

  count += 1

  if count % 285 == 0:
    hrUpdate += 1

writer.release()