import torch
import torch.nn as nn
import numpy as np
import cv2
from app.models.base import Segmenter
from app.core.config import settings

def double_conv(cin, cout):
    return nn.Sequential(
        nn.Conv2d(cin, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
        nn.Conv2d(cout, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
    )

class UNet(nn.Module):
    """U-Net для многоклассовой сегментации транспортных средств."""

    def __init__(self, in_ch=3, num_classes=4, base=32):
        super().__init__()
        self.d1 = double_conv(in_ch, base)
        self.d2 = double_conv(base, base * 2)
        self.d3 = double_conv(base * 2, base * 4)
        self.pool = nn.MaxPool2d(2)
        self.bottleneck = double_conv(base * 4, base * 8)
        self.u3 = nn.ConvTranspose2d(base * 8, base * 4, 2, stride=2)
        self.c3 = double_conv(base * 8, base * 4)
        self.u2 = nn.ConvTranspose2d(base * 4, base * 2, 2, stride=2)
        self.c2 = double_conv(base * 4, base * 2)
        self.u1 = nn.ConvTranspose2d(base * 2, base, 2, stride=2)
        self.c1 = double_conv(base * 2, base)
        self.head = nn.Conv2d(base, num_classes, 1)

    def forward(self, x):
        d1 = self.d1(x)
        d2 = self.d2(self.pool(d1))
        d3 = self.d3(self.pool(d2))
        b = self.bottleneck(self.pool(d3))
        u3 = self.c3(torch.cat([self.u3(b), d3], dim=1))
        u2 = self.c2(torch.cat([self.u2(u3), d2], dim=1))
        u1 = self.c1(torch.cat([self.u1(u2), d1], dim=1))
        return self.head(u1)


class UNetSegmenter(Segmenter):
    def __init__(self, weights_path: str | None = None, device: str | None = None):
        self.device = device or settings.device
        self.net = UNet(num_classes=len(settings.classes) + 1).to(self.device)
        if weights_path:
            state = torch.load(weights_path, map_location=self.device)
            self.net.load_state_dict(state)
        self.net.eval()

    def segment(self, frame_bgr: np.ndarray) -> np.ndarray:
        img = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (512, 512)).astype(np.float32) / 255.0
        x = torch.from_numpy(img).permute(2, 0, 1).unsqueeze(0).to(self.device)
        with torch.no_grad():
            logits = self.net(x)
            mask = logits.argmax(dim=1).squeeze(0).cpu().numpy().astype(np.uint8)
        return cv2.resize(mask, (frame_bgr.shape[1], frame_bgr.shape[0]),
                          interpolation=cv2.INTER_NEAREST)

    def classes(self) -> list[str]:
        return ["background", *settings.classes]
