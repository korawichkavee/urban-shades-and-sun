from ultralytics import YOLO

model = YOLO('yolo11n.pt')
results = model.train(data = '/home/kieran/Documents/Python/sunny_day_SVI/finetuning_yolo_test_imgs/project-8/data.yaml',epochs = 1000,save = True)
