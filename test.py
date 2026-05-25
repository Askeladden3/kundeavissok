from google import genai
from google.genai import errors


api_key = "AIzaSyBKCN8megAwQ7vbMznljmyBVi8J2eeNaXM"



















prompt = """You are provided with a list of JSON items from a norwegian grocery store. 
Your goal is to determine which of these items (and thus their URLs) that displays the sales for different food items for this current week (known as a kundeavis)
there are often other URLs that contain special promotions independent from the actual kundeavis. It is important that you do not choose these, even if they are valid for the current week.

return the URL from the correct item list when you are finished identifying it.
"""

URL_info = r"""[[{'@type': 'CreativeWork', 'name': 'Obs City Lade', 'image': 'https://image-transformer-api.tjek.com/?u=s3%3A%2F%2Fsgn-prd-assets%2Fuploads%2FueS-BLrr%2Fp-1.webp&w=250&s=fd682cb653e771495827451ed8373be9', 'url': 'https://etilbudsavis.no/Obs/?publication=ueS-BLrr'}, 'Obs City Lade', 'https://etilbudsavis.no/Obs/?publication=ueS-BLrr'],
                [{'@type': 'CreativeWork', 'name': 'Alt til grillsesongen', 'image': 'https://image-transformer-api.tjek.com/?u=s3%3A%2F%2Fsgn-prd-assets%2Fuploads%2FkE7AtTAv%2Fp-1.webp&w=250&s=3a07aaa61aaebcdbdb855481d72f7374', 'url': 'https://etilbudsavis.no/Obs/?publication=kE7AtTAv'}, 'Alt til grillsesongen', 'https://etilbudsavis.no/Obs/?publication=kE7AtTAv'], 
                [{'@type': 'CreativeWork', 'name': '', 'image': 'https://image-transformer-api.tjek.com/?u=s3%3A%2F%2Fsgn-prd-assets%2Fuploads%2Fo_AhE199%2Fp-1.webp&w=250&s=958f2aa5e3f4784e946518a439e4bd4a',"""


URL_info2 = r""" [
        [
            {
                "@type": "CreativeWork",
                "name": "Sommermat",
                "image": "https://image-transformer-api.tjek.com/?u=s3%3A%2F%2Fsgn-prd-assets%2Fuploads%2FBzhe9vZC%2Fp-1.webp&w=250&s=3fbc77a481c81565f49d91108645ab5a",
                "url": "https://etilbudsavis.no/Coop-Mega/?publication=Bzhe9vZC"
            },
            "Sommermat",
            "https://etilbudsavis.no/Coop-Mega/?publication=Bzhe9vZC"
        ],
        [
            {
                "@type": "CreativeWork",
                "name": "",
                "image": "https://image-transformer-api.tjek.com/?u=s3%3A%2F%2Fsgn-prd-assets%2Fuploads%2F0sbQvRbm%2Fp-1.webp&w=250&s=389bab462df5dd9fd14d756afe837a4b",
                "url": "https://etilbudsavis.no/Coop-Mega/?publication=0sbQvRbm"
            },
            "",
            "https://etilbudsavis.no/Coop-Mega/?publication=0sbQvRbm"
        ],
        [
            {
                "@type": "CreativeWork",
                "name": "Coop Mega Valentinlyst",
                "image": "https://image-transformer-api.tjek.com/?u=s3%3A%2F%2Fsgn-prd-assets%2Fuploads%2F_Rr5W0Pb%2Fp-1.webp&w=250&s=a01aa553fcd0cc79a7ee64bd3b8ffba9",
                "url": "https://etilbudsavis.no/Coop-Mega/?publication=_Rr5W0Pb"
            },
            "Coop Mega Valentinlyst",
            "https://etilbudsavis.no/Coop-Mega/?publication=_Rr5W0Pb"
        ]"""

with genai.Client(api_key=api_key) as client:
    response = client.models.generate_content(
    model='gemini-3.5-flash',
    contents=[prompt, URL_info2]
    )
    print(response.text)