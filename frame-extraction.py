import os
import cv2
import numpy as np
import sys
import json
import datetime
import ffmpeg

# ToDo: Write a README
# ToDo: Simplify moving HR to one of the corners of the image
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

timestampedHR = []
timestampedKCAL = []

data = json.load(workoutDataPath)

min = "00:00:00"
max = str(datetime.time(0, int(usefulMeta[3] / 60), usefulMeta[3] % 60))
for i in data["laps"][0]["points"]:
      readingTime = datetime.datetime.fromtimestamp(i.get("time"))
      delta = readingTime - usefulMeta[4] if readingTime > usefulMeta[4] else "00:00:00"
      if datetime.datetime.strptime(str(delta), "%H:%M:%S") > datetime.datetime.strptime(min, "%H:%M:%S"):
        if datetime.datetime.strptime(str(delta), "%H:%M:%S") <= datetime.datetime.strptime(max, "%H:%M:%S"):
          if i.get("hr"):
            timestampedHR.append([readingTime, i.get("hr")])
          if i.get("kcal"):
            timestampedKCAL.append([readingTime, i.get("kcal")])
        
timestampedHR.sort()
timestampedKCAL.sort()

print(len(timestampedHR))
print(len(timestampedKCAL))

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
kcal = timestampedKCAL[hrUpdate][1]

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

      font = cv2.FONT_HERSHEY_SIMPLEX

      bg_color = (0,0,0)
      
      try:
        hrFrame = np.full((sqrFrame.shape), bg_color, dtype=np.uint8)
        kcalFrame = np.full((sqrFrame.shape), bg_color, dtype=np.uint8)
      except:
        pass
      
      cv2.putText(hrFrame, str(timestampedHR[hrUpdate][1]), (80, sqrFrame.shape[1] - 200), font, 7, (0, 0, 255), 10, cv2.LINE_AA)
      cv2.putText(kcalFrame, str(f'{kcal:.2f}'), (80, 200), font, 7, (0, 0, 255), 10, cv2.LINE_AA)

      xHR,yHR,wHR,hHR = cv2.boundingRect(hrFrame[:,:,2])
      xKCAL,yKCAL,wKCAL,hKCAL = cv2.boundingRect(kcalFrame[:,:,2])
      
      xHR -= textPadding
      yHR -= textPadding
      hHR += textPadding * 2
      wHR += textPadding * 2 + hHR

      xKCAL -= textPadding
      yKCAL -= textPadding
      hKCAL += textPadding * 2
      wKCAL += textPadding * 2 + hKCAL

      hrFrame[yHR:yHR+180,xHR+wHR-180:xHR+wHR,:] = heart[0:180,0:180,:]
      
      try:
        result = sqrFrame.copy()
      except:
        pass

      result[yHR:yHR+hHR, xHR:xHR+wHR] = hrFrame[yHR:yHR+hHR, xHR:xHR+wHR]
      result[yKCAL:yKCAL+hKCAL, xKCAL:xKCAL+wKCAL] = kcalFrame[yKCAL:yKCAL+hKCAL, xKCAL:xKCAL+wKCAL]
      
      writer.write(result)

      count += 1

      if count % usefulMeta[2] == 0:
        time += datetime.timedelta(0,1)
      
      if time < timestampedHR[hrUpdate][0]:
        pass
      elif time >= timestampedHR[hrUpdate][0] and hrUpdate < len(timestampedHR) - 1:
        hrUpdate += 1
        kcal += timestampedKCAL[hrUpdate][1]
        
      frameIndex += 1

else:
  success,currentFrame = vidcap.read()
  frameIndex = 0
  while success:
      if orientation == "Horizontal":
        sqrFrame = cv2.copyMakeBorder(currentFrame, int((usefulMeta[0] - usefulMeta[1]) / 2), int((usefulMeta[0] - usefulMeta[1]) / 2), 0, 0, cv2.BORDER_CONSTANT, 0)
      else:
        sqrFrame = cv2.copyMakeBorder(currentFrame, 0, 0, int((usefulMeta[1] - usefulMeta[0]) / 2), int((usefulMeta[1] - usefulMeta[0]) / 2), cv2.BORDER_CONSTANT, 0)
      
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
        pass

      result[y:y+h, x:x+w] = bg[y:y+h, x:x+w]
      
      writer.write(result)

      count += 1

      if count % usefulMeta[2] == 0:
        time += datetime.timedelta(0,1)
      
      if time < timestampedHR[hrUpdate][0]:
        pass
      elif time >= timestampedHR[hrUpdate][0] and hrUpdate < len(timestampedHR) - 1:
        hrUpdate += 1
        
      frameIndex += 1

writer.release()
os.rename(videoPath, os.path.join(parent, "Done", videoFile))
os.rename(os.path.join(parent, workoutDataFile), os.path.join(parent, "Done", workoutDataFile))
os.rename(os.path.join(parent, "overlayed.mov"), os.path.join(parent, "Exports", str(datetime.datetime.today().replace(microsecond=0)).replace(" ", "_") + ".mov"))