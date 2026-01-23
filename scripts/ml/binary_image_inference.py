import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models, transforms
from torch.utils.data import DataLoader, Subset
from torchvision.datasets import ImageFolder
from sklearn.model_selection import StratifiedKFold
import numpy as np
from tqdm import tqdm
from PIL import Image

# -----------------------
# 1. Data preprocessing
# -----------------------
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=(0.5, 0.5, 0.5),
                         std=(0.5, 0.5, 0.5))  # scale to [-1, 1]
])


# Recreate the architecture exactly as during training
model = models.vit_b_16(pretrained=False)  # pretrained=False avoids re-downloading
model.heads = nn.Sequential(
    nn.Linear(model.heads.head.in_features, 1)
)

# Load weights
model.load_state_dict(torch.load("vit_binary.pth", map_location="cpu"))
model.eval()  # important for inference

img = Image.open("test_image.jpg").convert("RGB")
x = transform(img).unsqueeze(0)  # add batch dimension

with torch.no_grad():
    output = model(x).squeeze(1)
    prob = torch.sigmoid(output).item()
    pred = 1 if prob > 0.5 else 0

print(f"Predicted class: {pred}, probability: {prob:.4f}")