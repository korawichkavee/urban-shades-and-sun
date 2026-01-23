from ultralytics import YOLO

model = YOLO('yolo11s.pt')
results = model.train(data = '/home/kieran/Documents/Python/sunny_day_SVI/city7sample/images_to_label/batch2/sunny_batch/data.yaml',epochs = 2,save = True)
#results = model.train(data = '/home/kieran/Documents/Python/sunny_day_SVI/city7sample/images_to_label/batch1/relabeled9-5/data.yaml',epochs = 2,save = True)
