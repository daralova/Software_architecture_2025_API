"""Обучение U-Net. Структура датасета:
data/train/images, data/train/masks, data/val/images, data/val/masks.
Маски — PNG с индексами классов: 0 фон, 1 car, 2 bus, 3 truck."""
import argparse
import torch
import torch.nn as nn
import cv2, os, glob
import numpy as np
from app.models.unet import UNet

def load_pairs(folder):
    images, masks = [], []
    for ip in sorted(glob.glob(os.path.join(folder, "images", "*.png"))):
        mp = ip.replace("images", "masks")
        img = cv2.cvtColor(cv2.imread(ip), cv2.COLOR_BGR2RGB)
        mask = cv2.imread(mp, cv2.IMREAD_GRAYSCALE)
        images.append(img.astype(np.float32) / 255.0)
        masks.append(mask.astype(np.int64))
    return images, masks

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--out", default="checkpoints/unet.pth")
    args = ap.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = UNet().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    loss_fn = nn.CrossEntropyLoss()

    x_train, y_train = load_pairs(os.path.join(args.data, "train"))
    x_val, y_val = load_pairs(os.path.join(args.data, "val"))
    H, W = 512, 512

    def to_tensors(imgs, masks):
        X = torch.tensor([cv2.resize(i, (W, H)).transpose(2, 0, 1) for i in imgs])
        Y = torch.tensor([cv2.resize(m, (W, H), interpolation=cv2.INTER_NEAREST) for m in masks])
        return X, Y

    X, Y = to_tensors(x_train, y_train)
    Xv, Yv = to_tensors(x_val, y_val)
    dl = torch.utils.data.DataLoader(torch.utils.data.TensorDataset(X, Y),
                                     batch_size=args.batch, shuffle=True)

    best_iou = 0.0
    for epoch in range(args.epochs):
        model.train()
        total = 0.0
        for xb, yb in dl:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            opt.step()
            total += loss.item()
        model.eval()
        ious = []
        with torch.no_grad():
            pred = model(Xv.to(device)).argmax(1).cpu()
            for c in range(1, 4):
                inter = ((pred == c) & (Yv == c)).sum().item()
                union = ((pred == c) | (Yv == c)).sum().item()
                ious.append(inter / union if union else 1.0)
        miou = float(np.mean(ious))
        print(f"epoch {epoch + 1}: loss={total / len(dl):.4f} mIoU={miou:.4f}")
        if miou > best_iou:
            best_iou = miou
            os.makedirs("checkpoints", exist_ok=True)
            torch.save(model.state_dict(), args.out)
    print("Лучший mIoU:", round(best_iou, 4))

if __name__ == "__main__":
    main()
