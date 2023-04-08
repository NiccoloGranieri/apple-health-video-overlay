import os
import cv2
import numpy as np
import sys
import csv
import json
import datetime
import ffmpeg
import copy

# ToDo: Write a README
# ToDo: Simplify moving HR to one of the corners of the image
# ToDo: Start considering TimeStamps of every reading to make HR plotting more accurate
# ToDo: Start thinking of ways of automatically accepting videos from different cameras (i.e. GoPro)
# ToDo: Look at other data that could be potentially plotted
# ToDo: Re-Add audio to exported video 

parent = os.getcwd()
heart = cv2.imread("heart.png")

for file in os.listdir(parent):
    if file.lower().endswith(".mov"):
      videoFile = file
      videoPath = os.path.join(parent, file)
      videoProvenance = "iPhone"
    if file.lower().endswith(".mp4"):
      videoFile = file
      videoPath = os.path.join(parent, file)
      videoProvenance = "GoPro"
    if file.lower().endswith(".json"):
      workoutDataFile = file
      workoutDataPath = open(os.path.join(parent, file))

jsonMetadata = ffmpeg.probe(videoPath)

# print(jsonMetadata)

format = jsonMetadata["format"]

for i in jsonMetadata["streams"]:
  if i.get("index") == 0:
    vidW = i.get("width")
    vidH = i.get("height")    
    vidLen = int(float(i.get("duration")))
    nested = format["tags"]
    vidFR = float(i.get("r_frame_rate")[:-2])
    if videoProvenance != "GoPro":
      vidCrT = nested.get("com.apple.quicktime.creationdate")[:-5]
    else:
      vidCrT = nested.get("creation_time")[:-8]

adjVidCrT = datetime.datetime.strptime(vidCrT, '%Y-%m-%dT%H:%M:%S')
vidEndT = adjVidCrT + datetime.timedelta(seconds=vidLen)
usefulMeta = [vidW, vidH, vidFR, vidLen, adjVidCrT, vidEndT]

# print(usefulMeta)

hr = []
timestampedHR = []

data = json.load(workoutDataPath)

min = "00:00:00"
max = str(datetime.time(0, int(usefulMeta[3] / 60), usefulMeta[3] % 60))

for i in data["laps"][0]["points"]:
    if i.get("hr"):
        hrTime = datetime.datetime.fromtimestamp(i.get("time"))
        delta = hrTime - usefulMeta[4]
        try:
          if datetime.datetime.strptime(str(delta), "%H:%M:%S") >= datetime.datetime.strptime(min, "%H:%M:%S"):
            if datetime.datetime.strptime(str(delta), "%H:%M:%S") <= datetime.datetime.strptime(max, "%H:%M:%S"):
              hr.append(i.get("hr"))
              timestampedHR.append([hrTime, i.get("hr")])
        except:
           pass
        
timestampedHR.sort()
print(timestampedHR)

hrFrameUpdate = (usefulMeta[2] * vidLen) / len(hr)

vidcap = cv2.VideoCapture(videoPath)

count = 0

if usefulMeta[0] > usefulMeta[1]:
  orientation = "Horizontal"
  width = usefulMeta[0]
  height = usefulMeta[1] + (usefulMeta[0] - usefulMeta[1])
elif usefulMeta[0] < usefulMeta[1]:
  orientation = "Vertical"
  width = usefulMeta[0] + (usefulMeta[1] - usefulMeta[0])
  height = usefulMeta[1]
else:
  width = usefulMeta[0]
  height = usefulMeta[1]

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(sys.path[0] + "/overlayed.mov", fourcc, usefulMeta[2], (width, height))

count = 0
hrUpdate = 0
textPadding = 10
time = usefulMeta[4]

print("Processing video...")
if videoProvenance == "GoPro":
  expectedFrameCount = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
  frameIndex = 0

  while frameIndex < expectedFrameCount and frameIndex >= 0:
      print("Frame {} of {}".format(frameIndex, expectedFrameCount))
      ret, frame = vidcap.read()
      
      if orientation == "Horizontal":
        sqrFrame = cv2.copyMakeBorder(frame, int((usefulMeta[0] - usefulMeta[1]) / 2), int((usefulMeta[0] - usefulMeta[1]) / 2), 0, 0, cv2.BORDER_CONSTANT, 0)
      else:
        sqrFrame = cv2.copyMakeBorder(frame, 0, 0, int((usefulMeta[1] - usefulMeta[0]) / 2), int((usefulMeta[1] - usefulMeta[0]) / 2), cv2.BORDER_CONSTANT, 0)
      
      if not ret:
        frameIndex -= 1
        continue

      # if not frameIndex % 4 == 0:
      #   frameIndex += 1
      #   continue

      font = cv2.FONT_HERSHEY_SIMPLEX

      bg_color = (0,0,0)
      
      try:
        bg = np.full((sqrFrame.shape), bg_color, dtype=np.uint8)
      except:
        pass
      
      cv2.putText(bg, str(timestampedHR[hrUpdate][1]), (80, sqrFrame.shape[1] - 200), font, 7, (0, 0, 255), 10, cv2.LINE_AA)

      x,y,w,h = cv2.boundingRect(bg[:,:,2])
      
      x -= textPadding
      y -= textPadding
      h += textPadding * 2
      w += textPadding * 2 + h

      bg[y:y+180,x+w-180:x+w,:] = heart[0:180,0:180,:]
      
      try:
        result = sqrFrame.copy()
      except:
        print(frame)

      result[y:y+h, x:x+w] = bg[y:y+h, x:x+w]
      
      writer.write(result)

      count += 1

      # if count % int(hrFrameUpdate) == 0 and hrUpdate < len(hr) - 1:
      #   hrUpdate += 1

      if count % usefulMeta[2] == 0:
        time += datetime.timedelta(0,1)
      
      if time < timestampedHR[hrUpdate][0]:
        pass
      elif time >= timestampedHR[hrUpdate][0] and hrUpdate < len(timestampedHR) - 1:
        hrUpdate += 1
        
      frameIndex += 1

else:
  success,currentFrame = vidcap.read()
  while success:
    font = cv2.FONT_HERSHEY_SIMPLEX

    bg_color = (0,0,0)
    bg = np.full((currentFrame.shape), bg_color, dtype=np.uint8)

    cv2.putText(bg, str(hr[hrUpdate]), (80, 1000), font, 3, (0, 0, 255), 2, cv2.LINE_4)

    x,y,w,h = cv2.boundingRect(bg[:,:,2])

    bg[y:y+66,x+w+5:x+w+71,:] = heart[0:66,0:66,:]

    x -= textPadding
    y -= textPadding
    w += textPadding * 2 + 66
    h += textPadding * 2
    result = currentFrame.copy()
    result[y:y+h, x:x+w] = bg[y:y+h, x:x+w]

    writer.write(result)

    success,currentFrame = vidcap.read()

    count += 1

    if count % int(hrFrameUpdate) == 0 and hrUpdate < len(hr) - 1:
      hrUpdate += 1

writer.release()
os.rename(videoPath, os.path.join(parent, "Done", videoFile))
os.rename(os.path.join(parent, workoutDataFile), os.path.join(parent, "Done", workoutDataFile))
os.rename(os.path.join(parent, "overlayed.mov"), os.path.join(parent, "Exports", str(datetime.datetime.today().replace(microsecond=0)).replace(" ", "_") + ".mov"))