import gspread
import re
import mysql.connector
from googletrans import Translator
translator = Translator()
import csv

# connect to the google_sheet
client = gspread.service_account(filename="65b47311f305.json")
sheet = client.open('Products')
sheet_instance = sheet.get_worksheet(10)

# connect to the database
cnx = mysql.connector.connect(user='root', password='root',
                              host='localhost',
                              database='kilimi')
cur = cnx.cursor()

										
# define custom product features
attr_name={'Тканина':'material', 'Склад':'attr_sostav', 'Колір':'color', 'Країна':'Туреччина'}

filter_name ={'Колір':'color', 'Цiна':'$$', 'Розмір':'size', 'Матеріал':'material', 'Категорія':'type'}

# match and reassign colors from scraping data with color names in our database 
def get_colour(color):
	with open('colour.csv', 'r', encoding='UTF8') as file:
		reader = csv.reader(file)
		for row in reader:
			if color == row[0]:
				return row[1]


# get values from google_sheets (list of dict)
products_list = list(filter(lambda x: len(x['name'])>0, sheet_instance.get_all_records()))

# language codes in product_attributes   
attr_lang=[2,3]


for i in products_list:

	# insert product in main table 
	cur.execute("""SELECT product.id FROM product WHERE seo_url=%s""", (i['seo_url'],)) 
	result = cur.fetchone()
	if result is None:
		cur.execute("""INSERT INTO product (name, name_ru, text, text_ru, h1, h1_ru, seo_url, models, img, 
			category_id, parent_id, statuse, sort, counts, subtract, stock_status, special, new) 
			VALUES ( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s )""", 
			(i['name'].strip(), i['name_ru'], i['dsc'], i['dsc_rus'], i['name'].strip(), i['name_ru'], i['seo_url'], i['seo_url'], '/uploads/textille/'+i['main_img'], 
				249, 256, 1, 3, 9999, 0, 1, 0, 0) )
		cnx.commit()

		if len(i['brand'])>1:
			cur.execute("""UPDATE product SET manufacturer_id = (SELECT id FROM manufacture WHERE name=%s) WHERE seo_url=%s""", (i['brand'], i['seo_url']))
			cnx.commit()

		# insert each pair size:price
		n=0
		for itm in str(i['size']).split(';'):
			size = itm	
			price = i['price'].split(';')[n]
			price = round((int(i['price'])*1.19)/32)
			cur.execute("""INSERT INTO price_product (product_id, type_price, type_price_ru, value) 
				VALUES ((SELECT product.id FROM product WHERE seo_url=%s), %s, %s, %s)""", (i['seo_url'], size, size, price))
			cnx.commit()
			n+=1

		# insert additional images
		if len(i['add_img_list'])>1:
			img_list=i['add_img_list'].strip(';').split(';')
			img_list.append('khalaty/size_chart_ua.png')
			for item in img_list:
				cur.execute("""INSERT INTO img_product (product_id, img) VALUES ((SELECT product.id FROM product WHERE seo_url=%s), %s)""", (i['seo_url'], '/uploads/textille/'+item))
				cnx.commit()
		else:
			cur.execute("""INSERT INTO img_product (product_id, img) VALUES ((SELECT product.id FROM product WHERE seo_url=%s), %s)""", (i['seo_url'], '/uploads/textille/khalaty/size_chart_ua.png'))
			cnx.commit()

		# insert product features 
		for item in attr_name:
			for lang in attr_lang:
				if item == 'Країна':
					attr_value = attr_name[item]
				else:
					attr_value = i[attr_name[item]]

				if len(attr_value)>1:
					if lang==2:
						attr_value = translator.translate(attr_value, dest='ru').text
					cur.execute("""INSERT INTO product_atrybuty (atrybuty_id, product_id, value, lang)
					 VALUES ((SELECT id FROM atrybuty WHERE name=%s), (SELECT product.id FROM product WHERE seo_url=%s), %s, %s)""", 
					 (item, i['seo_url'], attr_value, lang))
					cnx.commit()
					print(item, i['seo_url'], attr_value, lang)

		# product filters data 
		for item in filter_name:
			if item != 'Розмір':	
				filter_value=''
				if item=='Цiна':
					filter_value=filter_name[item]
				elif item=='Колір':
					filter_value=get_colour(i[filter_name[item]])
				else:
					filter_value=i[filter_name[item]]
					
				cur.execute("""SELECT filter_id, id FROM filter WHERE filter_name=%s and name=%s""", 
					 (item, filter_value))
				filters = cur.fetchone()
				if filter_value is not None:
					cur.execute("""INSERT INTO product_filter (fname_id, filter_id, product_id, value)
						 VALUES (%s, %s, (SELECT product.id FROM product WHERE seo_url=%s), %s)""", 
						 (filters[0], filters[1], i['seo_url'], filter_value))
					cnx.commit()
			else:
				for itm in i['size'].split(';'):
					itm = re.sub(r'\s\(.+','',itm)  # insert only sizes first letter
					cur.execute("""SELECT filter_id, id FROM filter WHERE filter_name=%s and name=%s""", 
					 (item, itm))
					filters = cur.fetchone()
					if filter_value is not None:
						cur.execute("""INSERT INTO product_filter (fname_id, filter_id, product_id, value)
							 VALUES (%s, %s, (SELECT product.id FROM product WHERE seo_url=%s), %s)""", 
							 (filters[0], filters[1], i['seo_url'], itm))
						cnx.commit()




cnx.close()