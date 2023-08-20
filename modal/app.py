import modal
from modal import method
import os
import json
import math

def download_model_to_folder():
    from fashion_clip.fashion_clip import FashionCLIP
    fclip = FashionCLIP('fashion-clip')


image = modal.Image.debian_slim().pip_install(
    [
        "requests",
        "fashion-clip",
        "pillow",
        "numpy",
        "pinecone-client"
    ]
).run_function(
    download_model_to_folder,
)

stub = modal.Stub("walmart-embeddings", image=image)

remote_vol = modal.NetworkFileSystem.persisted("remote")




@stub.cls(network_file_systems={"/remote": remote_vol})
class GPUFunctions:
    def __enter__(self):
        import pinecone
        pinecone.init(api_key=os.getenv('PINECONE_API_KEY'), environment=os.getenv('PINECONE_REGION'))
        self.index = pinecone.Index("myntra-image-index")
        from fashion_clip.fashion_clip import FashionCLIP
        self.fclip = FashionCLIP('fashion-clip')
    
    @method()
    def generate_embeddings(self, bulk_image_data):
        import numpy as np
        from PIL import Image
        images = []
        for image_data in bulk_image_data:
            image = Image.open(image_data["img_path"])
            images.append(image)
        try:
            image_embeddings = self.fclip.encode_images(images, batch_size=len(bulk_image_data))
            image_embeddings = image_embeddings/np.linalg.norm(image_embeddings, ord=2, axis=-1, keepdims=True)

            for i, image_data in enumerate(bulk_image_data):
                image_data["image_embedding"] = np.ndarray.tolist(image_embeddings[i])
            
            return bulk_image_data
        except:
            raise Exception("Error generating embeddings")
        

    @method()
    def pinecone_upsert(self, bulk_image_data):
        pinecone_data = []
        for image_data in bulk_image_data:
            img_embeds = image_data["image_embedding"]
            img_metadata = image_data
            img_metadata.pop("image_embedding")
            pinecone_data.append((image_data["id"], img_embeds, img_metadata))

        self.index.upsert(pinecone_data)
        
    @method()
    def pinecone_search(self, img_url):
        import numpy as np
        from PIL import Image
        import requests
        from io import BytesIO

        response = requests.get(img_url)
        print(response, img_url)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content))
            image_embeddings = self.fclip.encode_images([image], batch_size=1)
            image_embeddings = image_embeddings/np.linalg.norm(image_embeddings, ord=2, axis=-1, keepdims=True)
            embed = np.ndarray.tolist(image_embeddings[0])
            res = self.index.query(embed, top_k=3, include_metadata=True)
            print(res)
        else:
            raise Exception("Failed to download image")

def cleanse_data(data):
    for key, value in data.items():
        if isinstance(value, dict):
            cleanse_data(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                   cleanse_data(item)
        else:
            if value is None:
                data[key] = '' # Assuming you'd like to replace None with empty string
    return data

@stub.function(network_file_systems={"/remote": remote_vol})
def download_image(obj):
    import uuid
    import requests
    obj = cleanse_data(obj)
    if obj["img_path"] != "" or obj["id"] != "":
        return obj
    url = obj["img_url"]
    id = str(uuid.uuid4())
    obj["id"] = id
    if url == "":
        # print("No image url provided")
        obj["img_path"] = ""
    else:
        if not os.path.exists("/remote/images"):
            os.makedirs("/remote/images")
        filename = '/remote/images/' + id + '.jpg'
        if(os.path.exists(filename)):
            print(f"Image already exists as {filename}")
            obj["img_path"] = filename
        else:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    with open(filename, 'wb') as file:
                        file.write(response.content)
                        # print(f"Image downloaded and saved at {filename}")
                    obj["img_path"] = filename
                else:
                    print(f"Failed to download image {id}: {response}")
                    obj["img_path"] = ""
            except Exception as e:
                print(f"Failed to download image {filename}: {e}")
                obj["img_path"] = ""
    return obj

@stub.function(network_file_systems={"/remote": remote_vol})
def download_batch(data):
    data_list = list(download_image.map(data))
    removed_items = []
    for item in data_list:
        if item["img_path"] == "":
            data_list.remove(item)
            removed_items.append(item)
    print(f"Total items: {len(data_list)} / {len(data)}")
    return data_list    

@stub.function(network_file_systems={"/remote": remote_vol}, mounts=[modal.Mount.from_local_dir("/home/fresauce/vscode/walmart/mount", remote_path="/dbremote")])
def copy_db():
    import shutil
    if not os.path.exists("/remote/db"):
        os.makedirs("/remote/db")
    if not os.path.exists("/dbremote/myntra.db"):
        raise Exception("DB file does not exist")
    if not os.path.exists("/remote/db/myntra.db"):
        shutil.copyfile("/dbremote/myntra.db", "/remote/db/myntra.db")
        print("DB copied")
    else:
        print("DB already exists")

@stub.function(network_file_systems={"/remote": remote_vol})
def read_db(batch_size, offset, table_name):
    import sqlite3
    import json

    json_data = []
    conn = sqlite3.connect('/remote/db/myntra.db')
    c = conn.cursor()
    c.execute(f"SELECT * FROM {table_name} LIMIT {batch_size} OFFSET {offset}")
    rows = c.fetchall()
    for row in rows:
        if(len(row) == 5):
            json_data.append({
                "id": "",
                "name": row[0],
                "brand": row[1],
                "price": row[2],
                "product_url": row[3],
                "img_url": row[4],
                "img_path": ""
            })
        elif(len(row) == 7):
            json_data.append({
                "id": row[0],
                "name": row[1],
                "brand": row[2],
                "price": row[3],
                "product_url": row[4],
                "img_url": row[5],
                "img_path": row[6]
            })
        else:
            raise Exception("Invalid number of columns")
    conn.close()
    return json_data

@stub.function(network_file_systems={"/remote": remote_vol})
def push_json_db(data_list):
    import sqlite3
    conn = sqlite3.connect('/remote/db/myntra.db')
    c = conn.cursor()
    # c.execute('''DROP TABLE IF EXISTS updated_products''')
    c.execute('''CREATE TABLE IF NOT EXISTS updated_products
                (id text, name text, brand text, price text, product_url text, img_url text, img_path text)''')
    for data in data_list:
        c.execute("INSERT INTO updated_products VALUES (:id, :name, :brand, :price, :product_url, :img_url, :img_path)", data)
    conn.commit()
    conn.close()
    return "Success"

@stub.function(network_file_systems={"/remote": remote_vol})
def list_files(directory_path):
    import os
    res = []
    for path, subdirs, files in os.walk(directory_path):
        for name in files:
            p = os.path.join(path, name)
            res.append(p)
    return res

@stub.function(network_file_systems={"/remote": remote_vol})
def upload_batch(gPUFunctions, batch_size, offset):
    input_data = read_db.call(batch_size, offset, "updated_products")
    bulk_image_data = gPUFunctions.generate_embeddings.call(input_data)
    gPUFunctions.pinecone_upsert.call(bulk_image_data)

@stub.local_entrypoint()
def main():
    # #get db total row count
    # import sqlite3
    # conn = sqlite3.connect('./mount/myntra.db')
    # c = conn.cursor()
    # c.execute("SELECT COUNT(*) FROM products")
    # total_rows = c.fetchone()[0]

    # batch_size = 100
    # args = []
    # offset = 24000
    # total_rows = len(read_db.call(40000, offset, "updated_products"))
    # print(f"Total rows: {total_rows}")
    gPUFunctions = GPUFunctions()
    searchUrl = 'https://serving.photos.photobox.com/618161642e3eb7cae477bca07d18ea69ca17aa82e1162a008d4d9b8a60fe69786d3d6100.jpg'
    gPUFunctions.pinecone_search.call(searchUrl)
    # for _ in range(math.ceil(total_rows/batch_size)):
    #     args.append((gPUFunctions, batch_size, offset))
    #     offset = offset + batch_size
    #     # input_data = read_db.call(batch_size, offset, "products")
    #     # data_list = download_batch.call(input_data)
    #     # push_json_db.call(data_list)
    #     # print(f"Batch {i} completed")
    # res = list(upload_batch.starmap(args))
    # # emb = gPUFunctions.generate_embeddings.call(upd)
    # gPUFunctions.pinecone_upsert.call({
    #     "id": 0,
    #     "data": upd
    # })
    # search = gPUFunctions.pinecone_search.call(upd[0]["img_path"])
    # print(search)
    # print(len(list_files.call("/remote/images")))
    # print(len(files))