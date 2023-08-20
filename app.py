from dotenv import load_dotenv
load_dotenv()

import boto3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from IPython.display import display
from io import BytesIO
from diffusers.utils import load_image
import uuid
import base64
from PIL import Image
from setup import pinecone_search,pipe3
import os
import requests
from transformers import BlipProcessor, BlipForConditionalGeneration, pipeline
import torch
import urllib
from bs4 import BeautifulSoup

processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to("cuda")

checkpoint = "MBZUAI/LaMini-Flan-T5-783M"
model_text = pipeline('text2text-generation', model = checkpoint)

def load_webp_image_from_link(image_url):
    response = requests.get(image_url)
    if response.status_code == 200:
        content = BytesIO(response.content)
        image = Image.open(content)
        return image
    else:
        print(f"Failed to load image from {image_url}. Status code: {response.status_code}")
        return None

def scraper(url):
    headers = {'User-Agent' : 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.89 Safari/537.36'}
    s = requests.Session()

    res = s.get(url, headers=headers, proxies=urllib.request.getproxies())

    soup=BeautifulSoup(res.content,"html.parser")

    imageCont=soup.find_all("li",class_='_20Gt85 _1Y_A6W _2_B7hD')

    img_urls=[]
    for image in imageCont:
        image_src=image.find('img').attrs['src']

        if image_src is not None:
            img_urls.append(image.find('img').attrs['src'])
        


    return img_urls

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

def upload_to_s3(image):
    image_bytes = BytesIO()
    image.save(image_bytes, format='JPEG')  # Adjust the format if needed
    image_bytes = image_bytes.getvalue()

    # Create a Boto3 S3 client
    s3_client = boto3.client('s3', aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'), aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'), region_name=os.getenv('AWS_BUCKET_REGION'))

    unique_filename = str(uuid.uuid4()) + '.jpeg'

    # Upload the image to S3 bucket
    response = s3_client.put_object(
        Bucket=os.getenv('AWS_BUCKET_NAME'),
        Key=unique_filename,
        Body=BytesIO(image_bytes),
        ACL='private'  # Set the desired ACL, e.g., private, public-read, authenticated-read, etc.
    )

    # Display the URL to the uploaded image if the ACL allows public access
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        print(f"Uploaded image successfully")
        return unique_filename
    else:
        print("Image upload failed.")

    return -1

@app.get("/")
def main():
    return {"message": "Hello World"}

class TextToImageRequestBody(BaseModel):
  prompt: str

class TextImageToImageRequestBody(BaseModel):
  prompt: str
  image: str

class TextMaskedImageToImageRequestBody(BaseModel):
  prompt: str
  image: str
  masked_image: str

class SimilarProductRequestBody(BaseModel):
  image: str

class RecommendationRequestBody(BaseModel):
  prompt: str
  products: list
  image: str
  masked_image: str

@app.post("/text-masked-image-to-image")
def text_masked_image_to_image(textMaskedImageToImageRequestBody: TextMaskedImageToImageRequestBody):
    masked_img_bytes = base64.b64decode(textMaskedImageToImageRequestBody.masked_image)
    masked_img = Image.open(BytesIO(masked_img_bytes))

    image = pipe3(prompt=textMaskedImageToImageRequestBody.prompt, image=load_image(textMaskedImageToImageRequestBody.image).convert("RGB"),mask_image=masked_img, num_inference_steps=50, strength=0.80).images[0]

    filename=upload_to_s3(image)

    # Return the image in the HTTP response
    return {'filename': filename}

@app.post("/get-similar-products")
def get_similar_products(similarProductRequestBody: SimilarProductRequestBody):
    similar_products = data=pinecone_search(similarProductRequestBody.image)
    metadata_list = [item['metadata'] for item in data['matches']]

    return {'products':metadata_list}

@app.post("/recommendation")
def recommendation(recommendationRequestBody:RecommendationRequestBody):
    product_urls=recommendationRequestBody.products
    img_urls=[]

    for product_url in product_urls:
        scraped_urls=scraper(product_url)
        img_urls+=scraped_urls

    raw_images=[]

    for img_url in img_urls:
        raw_images.append(load_webp_image_from_link(img_url))

    captions=recommendationRequestBody.prompt

    for raw_image in raw_images:
        prompt = "wearing "
        inputs = processor(raw_image, prompt, return_tensors="pt").to("cuda")
        out = model.generate(**inputs)
        captions+=processor.decode(out[0], skip_special_tokens=True)+" "

    input_prompt = "Give me a outfit recommendations based on the following information : "+captions
    generated_text = model_text(input_prompt, max_length=512, do_sample=True)[0]['generated_text']

    masked_img_bytes = base64.b64decode(recommendationRequestBody.masked_image)
    masked_img = Image.open(BytesIO(masked_img_bytes))

    image = pipe3(prompt=generated_text, image=load_image(recommendationRequestBody.image).convert("RGB"),mask_image=masked_img, num_inference_steps=50, strength=0.80).images[0]

    filename=upload_to_s3(image)

    # Return the image in the HTTP response
    return {'filename': filename}



import nest_asyncio
import uvicorn

nest_asyncio.apply()
uvicorn.run(app, port=8000)

