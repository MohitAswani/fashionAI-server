from diffusers import StableDiffusionXLPipeline,StableDiffusionXLInpaintPipeline,StableDiffusionXLImg2ImgPipeline
import torch
import pinecone
from fashion_clip.fashion_clip import FashionCLIP
import os

pipe3 = StableDiffusionXLInpaintPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0", torch_dtype=torch.float16, use_safetensors=True
)
pipe3.to("cuda")

pinecone.init(api_key=os.getenv('PINECONE_API_KEY'), environment=os.getenv('PINECONE_REGION'))
index = pinecone.Index("myntra-image-index")

fclip = FashionCLIP('fashion-clip')

def pinecone_search(img_url):
    import numpy as np
    from PIL import Image
    import requests
    from io import BytesIO

    response = requests.get(img_url)
    print(response, img_url)
    if response.status_code == 200:
        image = Image.open(BytesIO(response.content))
        image_embeddings = fclip.encode_images([image], batch_size=1)
        image_embeddings = image_embeddings/np.linalg.norm(image_embeddings, ord=2, axis=-1, keepdims=True)
        embed = np.ndarray.tolist(image_embeddings[0])
        res = index.query(embed, top_k=20, include_metadata=True)
        return res
    else:
        raise Exception("Failed to download image")