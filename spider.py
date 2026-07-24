import sqlite3
import ssl
import urllib.error
from urllib.request import urlopen
from urllib.parse import urljoin
from urllib.parse import urlparse
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

conn = sqlite3.connect("spider.sqlite")
cur = conn.cursor()

cur.execute('''create table if not exists Pages(id integer primary key autoincrement,
                                                url text unique, html text,
                                                error integer,
                                                old_rank real,
                                                new_rank real)''')
cur.execute('create table if not exists Links(from_id integer, to_id integer, primary key(from_id, to_id))')
cur.execute('create table if not exists Webs(url text unique)')

cur.execute('select id,url from Pages where html is Null and error is Null order by random() limit 1')
row = cur.fetchone()


if not row is None:
    print('Restart to do current scrawl')
else:
    starturl = input('Enter a website:')
    if len(starturl) < 1:
        starturl = 'https://www.jleague.co/'
    if starturl.endswith('/'):
         starturl = starturl[:-1]
    web = starturl
    if starturl.endswith('.htm') or starturl.endswith('.html'):
        pos = starturl.rfind('/')
        web = starturl[:pos]
    cur.execute('insert or ignore into Webs(url) values(?)', (web,))
    cur.execute('insert or ignore into Pages(url, html, new_rank) values(?, Null, 1.0)', (starturl,))
    conn.commit()

webs = list()
cur.execute('select url from Webs')
for row in cur:
    webs.append(str(row[0]))

many = 0
while True:
    if many < 1:
        sval = input("How many pages")
        if len(sval) < 1:
            break
        many = int(sval)
    many = many - 1
    
    cur.execute('select id,url from Pages where html is Null and error is Null order by random() limit 1')
    try:
        row = cur.fetchone()
        from_id = row[0]
        url = row[1]
    except:
        print("No page retrieved")
        continue
    
    cur.execute('delete from Links where from_id = ?', (from_id,))
    conn.commit()
    
    try:
        from urllib.request import Request, urlopen

        request = Request(
            url,
            headers={
                'User-Agent': 'RKCrawler/1.0 (learning project)'
                 }
            )

        document = urlopen(request, context=ctx)
        html = document.read()
        if document.getcode() != 200:
            print('Error opening the Page')
            cur.execute('update Pages set error = ? where url = ?', (document.getcode(), url))
            conn.commit()
        if document.info().get_content_type() != 'text/html':
            print('Ignore the webpage')
            cur.execute('delete from Pages where url = ?', (url,))
            conn.commit()
            continue
        soup = BeautifulSoup(html, 'html.parser')
    except KeyboardInterrupt:
        print('User Interruption')
        break
    except:
        cur.execute('update Pages set error = -1 where url = ?', (url,))
        conn.commit()
        continue
    
    cur.execute('update Pages set html = ? where url = ?', (memoryview(html), url))
    conn.commit()
        
    tags = soup('a')
    for tag in tags:
        href = tag.get('href', None)
        if href is None:
            continue
        up = urlparse(href)
        if len(up.scheme) < 1:
            href = urljoin(url, href)
        ipos = href.find('#')
        if ipos > 1:
            href = href[:ipos]
        if href.endswith('png') or href.endswith('jpg') or href.endswith('gif'):
            continue
        if href.endswith('/'):
            href = href[:-1]
        if len(href) < 1:
            continue
            
        found = False
        for web in webs:
            if href.startswith(web):
                found = True
                break
        if not found:
            continue
            
        cur.execute('insert or ignore into Pages(url, html, new_rank) values(?, Null, 1.0)', (href,))
        conn.commit()
         
        cur.execute('select id,url from Pages where url = ?', (href,))
        try:
            row = cur.fetchone()
            to_id = row[0]
        except:
            print('Cannot retrieve id')
            continue
        cur.execute('insert or ignore into Links(from_id, to_id) values(?,?)', (from_id, to_id))
        conn.commit()
conn.close()
