import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models, transforms
from torch.utils.data import DataLoader, Subset
from torchvision.datasets import ImageFolder
from sklearn.model_selection import StratifiedKFold
import numpy as np
from tqdm import tqdm

# -----------------------
# 1. Data preprocessing
# -----------------------
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=(0.5, 0.5, 0.5),
                         std=(0.5, 0.5, 0.5))  # scale to [-1, 1]
])

# Load entire dataset (all data in one folder, stratified split later)
dataset = ImageFolder("/home/kieran/Documents/Python/sunny_day_SVI/city7sample/images_to_label/batch2/labeled/data", transform=transform)

# Labels as numpy for stratification
targets = np.array([label for _, label in dataset.samples])

# -----------------------
# 2. Cross-validation setup
# -----------------------
kfold = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")




for fold, (train_idx, val_idx) in enumerate(kfold.split(np.zeros(len(targets)), targets)):
    print(f"\n----- Fold {fold+1} -----")

    # Create subsets for this fold
    train_subset = Subset(dataset, train_idx)
    val_subset   = Subset(dataset, val_idx)

    train_loader = DataLoader(train_subset, batch_size=32, shuffle=True)
    val_loader   = DataLoader(val_subset, batch_size=32)

    # -----------------------
    # 3. Load model fresh each fold
    # -----------------------
    model = models.vit_b_16(pretrained=True)
    model.heads = nn.Sequential(
        nn.Linear(model.heads.head.in_features, 1)  # single output
    )




    model.to(device)

    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-4)

    # -----------------------
    # 4. Training loop
    # -----------------------
    for epoch in range(5):  # adjust epochs
        model.train()
        running_loss = 0.0
        for images, labels in tqdm(train_loader):
            images, labels = images.to(device), labels.float().to(device)

            optimizer.zero_grad()
            outputs = model(images).squeeze(1)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * images.size(0)

        avg_train_loss = running_loss / len(train_subset)

        # validation
        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.float().to(device)
                outputs = model(images).squeeze(1)
                preds = (torch.sigmoid(outputs) > 0.5).long()
                correct += (preds == labels.long()).sum().item()
                total += labels.size(0)

        acc = correct / total
        print(f"Fold {fold+1}, Epoch {epoch+1}, Loss: {avg_train_loss:.4f}, Val Acc: {acc:.3f}")
        torch.save(model.state_dict(),'vit_binary.pth')
