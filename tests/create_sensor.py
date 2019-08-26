import ciao
from matplotlib import pyplot as plt

cam = ciao.cameras.SimulatedCamera()
sensor = ciao.sensors.Sensor(cam)

sensor.sense()
sensor.record_reference()

print dir(cam)
print dir(sensor)

sb = sensor.search_boxes
plt.imshow(sensor.image,cmap='gray',aspect='auto')
for x1,x2,y1,y2 in zip(sb.x1,sb.x2,sb.y1,sb.y2):
    plt.plot([x1,x2,x2,x1,x1],[y1,y1,y2,y2,y1],'y-')

plt.show()
