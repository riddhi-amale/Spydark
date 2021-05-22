import requests
from lxml import html
import collections
import urllib.parse
from requests.exceptions import HTTPError
import time
from stem import Signal
from stem.control import Controller
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from .utils import connect_mongodb, display_wordcloud
import os

TORCC_HASH_PASSWORD = "<torcc_password>"
TORCC_HASH_PASSWORD = "ToRhCPw17$"

class MiniCrawlbot:
    
    def __init__(self):
        import warnings
        warnings.filterwarnings("ignore")
        try:
            import requests.packages.urllib3
            requests.packages.urllib3.disable_warnings()
        except Exception:
            pass

        '''add time delay between each request to avoid DOS attack'''
        self.wait_time = 1
        
        '''socks proxies required for TOR usage'''
        self.proxies = {'http' : 'socks5h://127.0.0.1:9050', 'https' : 'socks5h://127.0.0.1:9050'}

    def get_current_ip(self):
        try:
            r = requests.get('http://httpbin.org/ip', proxies = self.proxies)
        except Exception as e:
            print (str(e))
        else:
            return r.text.split(",")[-1].split('"')[3]

    def renew_tor_ip(self):
        with Controller.from_port(port = 9051) as controller:
            controller.authenticate(password=TORCC_HASH_PASSWORD)
            controller.signal(Signal.NEWNYM)

    def is_alive(self, url):
        try:
            ua = UserAgent()
            user_agent = ua.random
            headers = {'User-Agent': user_agent}
            response = requests.get(url, proxies = self.proxies, headers = headers, timeout = 15)
            response.raise_for_status()
        except HTTPError as http_err:
            print(" Page not found..." + url)
            return False, None
        except Exception as err:
            print("Page not found..." + url )
            return False, None
        else:
            print("Page has found....")     
            return True, response

    def tor_crawler(self, keyUrl, depth, isKeyword):

        if isKeyword:
            query = str('+'.join(keyUrl.split(' ')))
            visitedcoll = connect_mongodb("dark-key-db", "keywords-visited")
            coll = connect_mongodb("dark-key-db", keyUrl)
        else:
            visitedcoll = connect_mongodb("dark-url-db", "seed-urls-visited")
            coll = connect_mongodb("dark-url-db", keyUrl)

        visited = False

        if isKeyword:
            for _ in visitedcoll.find({"Keyword":keyUrl}):
                visited = True
        else:
            for _ in visitedcoll.find({"seed-url":keyUrl}):
                visited = True

        links = []
        wc_words = open('users/static/users/wc_words.txt', 'w', encoding='utf-8')
        
        if visited:
            for x in coll.find():
                links.append(x["Link"])
                try:
                    wc_words.write(x["Page content"] + "\n\n")
                except Exception:
                    pass
        
        else:
            os.startfile("C:\Tor Browser\Browser\\firefox.exe")
            time.sleep(10)
            print("Tor Browser started")
            
            if isKeyword:
                url = 'http://msydqstlz2kzerdg.onion/search?q=' + query
            else:
                url = keyUrl

            ua = UserAgent()
            user_agent = ua.random
            headers = {'User-Agent': user_agent}
            r = requests.get(url, proxies = self.proxies, headers = headers)
            body = html.fromstring(r.content)
            s = BeautifulSoup(r.text, 'lxml')
            print(">>>>>>>>>", s.find("title").text.strip())
            if isKeyword:
                links_found = body.xpath('//h4/a/@href')      
            else:
                links_found = body.xpath('//a/@href')   
                print("HEREEEE", links_found, len(links_found))   

            if isKeyword:
                links = ["http://msydqstlz2kzerdg.onion/"]
            else:
                links = [keyUrl]

            urlq = collections.deque()
            
            seed_links = 0
            for link_found in links_found :
                link = link_found.split('url=')[-1]
                if not isKeyword and link[0] == "/":
                    link = url + link[1:]
                if link not in links:
                    urlq.append(link)
                    links.append(link)
                    seed_links += 1
                    print(link)
                    print("#"*20)
                if seed_links>=100:
                    break
                
            links_per_page = [1, len(links)-1]

            # number of pages to visit in one crawling session
            countpage = 0

            # number of total links harvested during crawling
            countlink = 1
            
            inactive_links = []

            try:	
                # cnt = 0
                while (len(urlq) != 0 and countpage != depth):
                    
                    '''pop url from queue'''
                    url = urlq.popleft()
                            
                    '''IP spoofing'''
                    current_ip = self.get_current_ip()
                    print("IP : {}".format(current_ip))
                    print("{}. Crawling {}".format(str(countpage+1), url))

                    # cnt += 1
                    if url == "http://ctemplarpizuduxk3fkwrieizstx33kg5chlvrh37nz73pv5smsvl6ad.onion/how-to-save-yourself-from-different-types-of-malware/" :
                        inactive_links.append(url)
                        print("Inactive link")
                        continue
                    
                    link_active, response = self.is_alive(url)
                    '''if link is active, visit link '''

                    if link_active :
                        
                        countpage += 1
                        
                        '''user agent spoofing'''
                        # ua = UserAgent()
                        # user_agent = ua.random
                        # headers = {'User-Agent': user_agent}
                        # print("User Agent is : {}".format(user_agent))
                            
                        '''send request to chosen site'''
                        # response = requests.get(url, proxies = self.proxies, headers = headers)
                        
                        body = html.fromstring(response.content)
                        
                                                    
                        '''links available on current web page'''
                        links_found = [urllib.parse.urljoin(response.url, url) for url in body.xpath('//a/@href')]
                        
                        no_of_links = 0

                        for link in links_found:
                            if link not in links:
                                urlq.append(link)
                                links.append(link)
                                print (str(countlink) +"{:<5}".format(" ")+ link, end= "\n\n" )
                                countlink += 1
                                no_of_links += 1

                            # Allow max 100 links from each site    
                            if no_of_links > 100:
                                break

                        links_per_page.append(no_of_links)

                    else:
                        inactive_links.append(url)
                        print("Inactive link")

                    '''Obtain new IP using TOR'''
                    self.renew_tor_ip()                
                    time.sleep(self.wait_time)
                                
            except Exception as e:
                print(str(e))

            print("Total links to parse:", len(links))
            print(">>>>>>>>PART 2>>>>>>>>>>>>>>")

            parent = None
            link_count = 1
            idx = 1
            parent_idx = -1

            for link in links:
                try:
                    current_ip = self.get_current_ip()
                    print("IP : {}".format(current_ip))
                    ua = UserAgent()
                    user_agent = ua.random
                    headers = {'User-Agent': user_agent}
                    print(link_count, "-> Parsing:", link)

                    source = requests.get(link, proxies = self.proxies, headers = headers, timeout = 15).text
                    curr_page = BeautifulSoup(source, 'lxml')
                    title = curr_page.find("title").text.strip()
                    text = ' '.join(curr_page.text.split())
                    wc_words.write(text + "\n\n")
                    active = True
                    print("Found")
                except Exception:
                    print("Not found")
                    active = False
                print("Parent:", parent)
                if active:
                    coll.insert_one({"Link":link, "Title":title, "Page content":text, "Parent link":parent, "Link status":"Active"})
                else:
                    coll.insert_one({"Link":link, "Parent link":parent, "Link status":"Inactive"})
                
                link_count += 1
                if sum(links_per_page[:idx])<link_count:
                    parent_idx += 1
                    parent = links[parent_idx]
                    idx += 1
                while parent in inactive_links:
                    parent_idx += 1
                    parent = links[parent_idx]

                self.renew_tor_ip()                
                time.sleep(self.wait_time)
                
            if isKeyword:
                visitedcoll.insert_one({"Keyword":keyUrl})
            else:
                visitedcoll.insert_one({"seed-url":keyUrl})

        topFiveWords = display_wordcloud(wc_words)

        # TODO(): Use 200 and 400 and response status codes to classify link status
        return links, topFiveWords


    def get_page_content(self, link):
        os.startfile("C:\Tor Browser\Browser\\firefox.exe")
        time.sleep(10)
        print("Tor Browser started")

        current_ip = self.get_current_ip()
        print("IP : {}".format(current_ip))
        ua = UserAgent()
        user_agent = ua.random
        headers = {'User-Agent': user_agent}

        source = requests.get(link, proxies = self.proxies, headers = headers, timeout = 15).text
        curr_page = BeautifulSoup(source, 'lxml')
        page_content = ' '.join(curr_page.text.split())
        print(">>>", page_content)
        return page_content

        
    def get_todays_status(self, flagged_links):
        os.startfile("C:\Tor Browser\Browser\\firefox.exe")
        time.sleep(10)
        print("Tor Browser started")

        todays_status = []

        for flagged_link in flagged_links:

            current_ip = self.get_current_ip()
            print("IP : {}".format(current_ip))
            ua = UserAgent()
            user_agent = ua.random
            headers = {'User-Agent': user_agent}

            try:
                source = requests.get(flagged_link, proxies = self.proxies, headers = headers, timeout = 15).text
                curr_page = BeautifulSoup(source, 'lxml')
                _ = curr_page.find("title").text.strip()
                active = True
                print("Found ->", flagged_link)
            except Exception:
                print("Not found ->", flagged_link)
                active = False
            
            todays_status.append(active)

            self.renew_tor_ip()                
            time.sleep(self.wait_time)

        return todays_status