import gspread
import urllib.request
import re
from bs4 import BeautifulSoup
from googletrans import Translator
import cyrtranslit

translator = Translator()

# define spreadsheet and worksheets to write data
client = gspread.service_account(filename="65b47311f305.json")
sheet = client.open('Products')
sheet_instance = sheet.get_worksheet(0)


def translit(text):   # return translited string 
    seo_url = cyrtranslit.to_latin(text, "ru")
    return re.sub(r'\'','',seo_url).lower().replace(' ','-')

def soup_open(link):  # return bs object as html string
    html_main = urllib.request.urlopen(link)
    return BeautifulSoup(html_main, 'html.parser')

def feature_weight():  # return value of product weight, if specified
    try:
        return soup(class_='woocommerce-product-attributes-item woocommerce-product-attributes-item--weight')[0].find('td').get_text()
    except:
        return None

def feature(fname):  # return value of product weight, if specified
    try:
        return soup(class_='woocommerce-product-attributes-item--attribute_pa_'+fname)[0].find('a', attrs={'rel':'tag'}).get_text()
    except:
        return None

def re_sub(replacements, string):
    for i in replacements:
        string = re.sub(i[0],i[1], string)
    return string


# def main(link, photo_f): # link - product category page, photo_f - folder name for saving images
link = 'https://kayra.ua/category/domashnij-odyag'

links=[]
links.append(link)
soup = soup_open(link)
pages = soup(class_='woocommerce-pagination')
pages = soup.find_all('a', attrs={'class':'page-number'})
if pages:
    n=int(pages[-2].get_text())
    p=2
    while p<=n:
        links.append(str(link+'/page/'+str(p)))
        p+=1

print(links)
products={}

for item in links:    
    soup = soup_open(item)
    prod_links = soup(class_='woocommerce-LoopProduct-link woocommerce-loop-product__link')
    for i in prod_links:
        name=i.get_text().replace('×','x').strip()
        # define replacement patterns for the re_sub func in order to convert names in proper value
        name_replacements = [
                    (r'\s{1,2}–\s|\s{2,}|,\s',' '),
                    (r'\s[хx]\s|х','x'), # replace cyrillic 'х' with latin 'x'
                    (r'[“”]','')
                    ]       
        name = re_sub(name_replacements, name)
        soup = soup_open(i.get('href'))
        price = re.sub(r'грн|\s','',soup(class_="woocommerce-Price-amount amount")[0].get_text())
        dsc = soup(id='tab-description')[0].get_text()
        
        # in the descriprion find the product features values we are interested in (in this case fabric composition)
        attr_sostav = re.search(r'(.клад:).{1,55}?(?=[\n])',dsc)
        if attr_sostav is not None:
            attr_sostav=attr_sostav.group(0)

        # define replacement patterns for the re_sub func in order to convert description text in proper form
        dsc_replacements = [
                    (r'Компанія\n[\s\S]+|[\s\S]+[Оо]пис\n|Увага![\s\S]+|[“”]', ''),
                    (r'\n{2,}', '\n'), 
                    (r'\n([\w\s:?]+?)\n', r'\n<h3>\1</h3>\n')
                    ]       
        dsc = re_sub(dsc_replacements, dsc)

        # translate description into assholes lang
        dsc_rus = translator.translate(dsc, src='uk', dest='ru').text

        # in the feature description find required values 
        brand = feature('brend')
        material = feature('tkanyna')
        color = feature('kolir')
        size = feature('rozmir')
        type_product = feature('stat')

        # remove brand from product name
        if brand is not None:
            name = name.replace(brand+' ', '')

        # if product has colour variations - split product into each of them, add colour value to the product name   
        var_names = []
        if soup(class_='vi-wpvs-select-attribute-attribute_pa_kolir'):
            colours_var = soup(class_='variations')[0].find(attrs={'data-attribute':'attribute_pa_kolir'})\
                            .find_all(class_='vi-wpvs-option-wrap vi-wpvs-option-wrap-default')
            for col in colours_var:
                color = col.get('data-attribute_label')
                var_names.append((name+' '+translator.translate(color, dest='en').text, \
                                    col.find(class_='vi-wpvs-option vi-wpvs-option-image').get('src').replace('-100x100',''), color))

        # if not - append only one product name
        else:
            var_names.append((name, soup(class_='woocommerce-product-gallery__image slide first')[0].find('a').get('href'), color))  

        for items in var_names:
            name = items[0] 
            color = items[2]
            name_ru = translator.translate(name, dest='ru').text.rstrip('.')
            seo_url = translit(name_ru) 
            seo_url = re.sub(r'[,():]','',seo_url).rstrip('-')

            print('============\n'+color+'\n'+seo_url+'\n'+name+'\n'+name_ru+'\n============')

        # images
            # specify the name of the folder to upload the photo 
            folder = 'khalaty/'
            photo = items[1]

            # define name, download and save main image
            main_img = folder+seo_url+".jpg"
            try:
                img = urllib.request.urlretrieve(photo, main_img)
            except UnicodeEncodeError:
                print('check img for '+seo_url)

            # download additional images, save defined names into ';'-separated string    
            add_img_string = ''
            if len(var_names) == 1:
                photo2 = soup(class_='woocommerce-product-gallery__image slide')
                n=2                
                if len(photo2) > 0: 
                    for i in photo2:
                        try:
                            add_img = folder+seo_url+"_"+str(n)+".jpg"
                            img = urllib.request.urlretrieve(i.find_all('a')[0].get('href'), add_img)

                            add_img_string += add_img+';'
                            n+=1
                        except:
                            print('can not save additional photo '+seo_url)
            
            #  if product page has more than 1 colour variations, and we cant assign them to the particular product,
            #     save images to overall folder inside main folder
            else:
                photo2 = soup(class_='woocommerce-product-gallery__image slide')
                n=2                
                if len(photo2) > 0: 
                    for i in photo2:
                        try:
                            add_img = folder+"add/"+name+"_"+str(n)+".jpg"
                            img = urllib.request.urlretrieve(i.find_all('a')[0].get('href'), add_img)
                            n += 1
                        except:
                            continue
            
            data = name, name_ru, seo_url, price, attr_sostav, brand, material, color, size, type_product, dsc, dsc_rus, main_img, add_img_string

            # in order to avoid duplicates, use unique seo_url as dict key            
            if seo_url not in products:
                products[seo_url]=list(data)

            # if product exists in dict - add here current variations of sizes prices accordingly
            else:
                if size not in products[seo_url][9]:
                    products[seo_url][3]=products[seo_url][3]+';'+price
                    products[seo_url][9]=products[seo_url][9]+';'+size

# insert dist values of product data into next free row in google_sheets
col_val = sheet_instance.col_values(1)
print_row=len(col_val)+2
sheet_instance.update('A{}'.format(print_row), list(products.values()))



