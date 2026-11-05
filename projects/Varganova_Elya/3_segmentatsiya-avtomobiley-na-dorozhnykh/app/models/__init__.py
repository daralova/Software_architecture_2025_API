from app.models.unet import UNetSegmenter
from app.models.segformer import SegFormerAdapter
from app.models.factory import register, create_segmenter, available

register("unet")(UNetSegmenter)
register("segformer")(SegFormerAdapter)
