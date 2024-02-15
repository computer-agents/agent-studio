def test_gemini():
    # model = genai.GenerativeModel('gemini-pro-vision')

    # cookie_picture = [{
    #     'mime_type': 'image/png',
    #     'data': Path('cookie.png').read_bytes()
    # }]
    # prompt = "Do these look store-bought or homemade?"

    # response = model.generate_content(
    #     model="gemini-pro-vision",
    #     content=[prompt, cookie_picture]
    # )
    # print(response.text)

    # model = genai.GenerativeModel('gemini-pro-vision')

    # prompt = "Write a story about a magic backpack."

    # response = model.generate_content(prompt)

    import google.generativeai as genai

    from playground.config import Config

    config = Config()

    GEMINI_API_KEY = config.GEMINI_API_KEY

    genai.configure(api_key=GEMINI_API_KEY)

    # for m in genai.list_models():
    #     if 'generateContent' in m.supported_generation_methods:
    #         print(m.name)

    # model = genai.GenerativeModel('gemini-pro')

    # response = model.generate_content("What is the meaning of life?")
    # print(response)
    # print(response.text)

    import PIL.Image

    model = genai.GenerativeModel("gemini-pro-vision")

    # img = PIL.Image.open('image.jpg')
    # # response = model.generate_content(img)
    # # print(response.text)
    # response = model.generate_content(["Write a short, engaging blog post based on this picture. It should include a description of the meal in the photo and talk about my journey meal prepping.", img])  # noqa: E501
    # print(response.text)

    import http.client
    import typing
    import urllib.request

    def get_image_bytes_from_url(image_url: str) -> bytes:
        with urllib.request.urlopen(image_url) as response:
            response = typing.cast(http.client.HTTPResponse, response)
            image_bytes = response.read()
        return image_bytes

    def load_image_from_url(image_url: str) -> PIL.Image:
        image_bytes = get_image_bytes_from_url(image_url)
        return PIL.Image.from_bytes(image_bytes)

    image_grocery_url = "https://storage.googleapis.com/github-repo/img/gemini/multimodality_usecases_overview/banana-apple.jpg"  # noqa: E501
    image_prices_url = "https://storage.googleapis.com/github-repo/img/gemini/multimodality_usecases_overview/pricelist.jpg"  # noqa: E501
    image_grocery = load_image_from_url(image_grocery_url)
    image_prices = load_image_from_url(image_prices_url)

    instructions = "Instructions: Consider the following image that contains fruits:"
    prompt1 = "How much should I pay for the fruits given the following price list?"
    prompt2 = """
    Answer the question through these steps:
    Step 1: Identify what kind of fruits there are in the first image.
    Step 2: Count the quantity of each fruit.
    Step 3: For each grocery in first image, check the price of the grocery in the price list.  # noqa: E501
    Step 4: Calculate the subtotal price for each type of fruit.
    Step 5: Calculate the total price of fruits using the subtotals.

    Answer and describe the steps taken:
    """

    contents = [
        instructions,
        image_grocery,
        prompt1,
        image_prices,
        prompt2,
    ]

    response = model.generate_content(contents)

    print(response.text)
