from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UserRegisterForm, SearchURL, SearchKeyword, SearchKeywordPlt, CrawlDropdownSelect, CustomSimilarityPlatformSelect, CustomSimilarityKeywordSelect
from django.contrib.auth.decorators import login_required

from .utils import addhistory, get_images, get_text, generate_wordcloud_dynamically, Dashboard, SurfaceURL, Instagram, Twitter
from .minicrawlbot import MiniCrawlbot
from .img_detect import detect_object
from .text_process import detect_text

# for passing arguments in redirect
from django.urls import reverse
from urllib.parse import urlencode
from datetime import datetime
import time

database = None
collection = None
iterativeCrawledKeywords = []
crawled_dropdown_choices = []

platform_choice = None
selected_database = None
visited_keywords_choices = []

def register(request):
    if request.method =='POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.info(request, f'Account created for {username}! Log In now!')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form':form, 'title':"Register Now"})    

@login_required
def welcome(request):
    return render(request, 'users/welcome.html', {'title':"Home"})

@login_required
def dashboard(request):
    global database
    global collection
    global iterativeCrawledKeywords
    global crawled_dropdown_choices
    global platform_choice
    global selected_database
    global visited_keywords_choices

    if request.method == "POST":
        database = None
        collection = None
        iterativeCrawledKeywords = []
        crawled_dropdown_choices = []

        platform_choice = None
        selected_database = None
        visited_keywords_choices = []
        
    if database is None or collection is None:
        return render(request, 'users/404.html', {'title':"Dashboard"})
    dash = Dashboard()
    links = dash.read_db(database, collection)
    return render(request, 'users/dashboard.html', {'links':links, 'title':"Dashboard"})


@login_required
def word_cloud(request):
    if database is None or collection is None:
        return render(request, 'users/404.html', {'title':"Wordcloud"})
    if len(iterativeCrawledKeywords)>0:
        if request.method =='POST':
            form = CrawlDropdownSelect(crawled_dropdown_choices, request.POST)
            if form.is_valid():
                crawled_choice = int(form.cleaned_data.get('crawled_choice'))
                generate_wordcloud_dynamically(database, iterativeCrawledKeywords, crawled_choice)
                return render(request, 'users/wordclouddash.html', {'title':"Wordcloud", 'form':form})
        else: 
            form = CrawlDropdownSelect(crawled_dropdown_choices)
            generate_wordcloud_dynamically(database, iterativeCrawledKeywords, 0)
        return render(request, 'users/wordclouddash.html', {'title':"Wordcloud", 'form':form, 'wc': True})
    return render(request, 'users/wordclouddash.html', {'title':"Wordcloud"})


@login_required
def active_links(request):
    if database is None or collection is None:
        return render(request, 'users/404.html', {'title':"Active links"})
    if len(iterativeCrawledKeywords)>0:
        if request.method =='POST':
            form = CrawlDropdownSelect(crawled_dropdown_choices, request.POST)
            if form.is_valid():
                crawled_choice = int(form.cleaned_data.get('crawled_choice'))
                dash = Dashboard()
                if crawled_choice < len(iterativeCrawledKeywords):
                    a, ia = dash.active_inactive(database, iterativeCrawledKeywords[crawled_choice])
                else:
                    a, ia = 0, 0
                    for iterativeCrawledKeyword in iterativeCrawledKeywords:
                        a_this, ia_this = dash.active_inactive(database, iterativeCrawledKeyword)
                        a += a_this
                        ia += ia_this
                return render(request, 'users/active_links.html', {'a':a, 'ia':ia, 'flag':True, 'title':"Active links", 'form':form})
        else:
            form = CrawlDropdownSelect(crawled_dropdown_choices)
            dash = Dashboard()
            a, ia = dash.active_inactive(database, collection)
            return render(request, 'users/active_links.html', {'a':a, 'ia':ia, 'flag':True, 'title':"Active links", 'form':form})
    dash = Dashboard()
    a, ia = dash.active_inactive(database, collection)
    return render(request, 'users/active_links.html', {'a':a, 'ia':ia, 'flag':True, 'title':"Active links"})


@login_required
def link_similarity(request):
    if len(iterativeCrawledKeywords)>0:
        dash = Dashboard()
        links, matrix, no_of_links, percentages, all_count = dash.display_link_similarity(database, iterativeCrawledKeywords)
        links_matrix = zip(links, matrix, percentages)
        total_links = len(links)
        keywords_nuumberOfLinks = zip(iterativeCrawledKeywords, no_of_links)
        return render(request, 'users/link_similarity.html', {'title':"Link Similarity", 'collections':keywords_nuumberOfLinks, 'links_matrix':links_matrix, 'total_links':total_links, 'all_count':all_count})
    
    else:
        global platform_choice
        global selected_database
        global visited_keywords_choices
        platform_choices = [
                (0,"--Select option--"),
                (1,"Surface (URL)"),
                (2,"Instagram"),
                (3,"Twitter"),
                (4,"Dark web (URL)"),
                (5,"Dark web (Keyword)")
            ]
        if request.method =='POST':
            select_platform_dropdown = CustomSimilarityPlatformSelect(platform_choices, request.POST)
            if select_platform_dropdown.is_valid():
                pltfrm_choice = select_platform_dropdown.cleaned_data.get('platform_choice')
                dash = Dashboard()
                sdb, vkc = dash.get_visited_keywords(pltfrm_choice)

                if pltfrm_choice!="":
                    platform_choice = pltfrm_choice
                    selected_database = sdb
                    visited_keywords_choices = vkc
                
                select_keyword_dropdown = CustomSimilarityKeywordSelect(visited_keywords_choices, request.POST)
                if select_keyword_dropdown.is_valid():
                    keyword_choices = select_keyword_dropdown.cleaned_data.get('keyword_choice')
                    selected_collections = []
                    for keyword_choice in keyword_choices:
                        selected_collections.append(visited_keywords_choices[int(keyword_choice)][1])
                    dash_selected = Dashboard()
                    links, matrix, no_of_links, percentages, all_count = dash_selected.display_link_similarity(selected_database, selected_collections)
                    links_matrix = zip(links, matrix, percentages)
                    keywords_nuumberOfLinks = zip(selected_collections, no_of_links)
                    total_links = len(links)
                    if len(links)>0:
                        return render(request, 'users/link_similarity.html', {'title':"Link Similarity", 'collections':keywords_nuumberOfLinks, 'links_matrix':links_matrix, 'total_links':total_links, 'all_count':all_count})
                return render(request, 'users/link_similarity.html', {'title':"Link Similarity", 'select_platform_dropdown':select_platform_dropdown, 'select_keyword_dropdown':select_keyword_dropdown})
        else: 
            select_platform_dropdown = CustomSimilarityPlatformSelect(platform_choices)
        return render(request, 'users/link_similarity.html', {'title':"Link Similarity", 'select_platform_dropdown':select_platform_dropdown})


@login_required
def link_tree(request):
    if database is None or collection is None:
        return render(request, 'users/404.html', {'title':"Link Tree"})
    if len(iterativeCrawledKeywords)>0:
        if request.method =='POST':
            form = CrawlDropdownSelect(crawled_dropdown_choices, request.POST)
            if form.is_valid():
                crawled_choice = int(form.cleaned_data.get('crawled_choice'))
                if crawled_choice < len(iterativeCrawledKeywords):
                    dash = Dashboard()
                    j = dash.create_tree(database, iterativeCrawledKeywords[crawled_choice])
                else:
                    j = None
                return render(request, 'users/link_tree.html', {'json':j, 'title':"Link Tree", 'form':form})
        else:
            form = CrawlDropdownSelect(crawled_dropdown_choices)
            dash = Dashboard()
            j = dash.create_tree(database, collection)
            return render(request, 'users/link_tree.html', {'json':j, 'title':"Link Tree", 'form':form})
    dash = Dashboard()
    j = dash.create_tree(database, collection)
    return render(request, 'users/link_tree.html', {'json':j, 'title':"Link Tree"})


@login_required
def surface(request):
    global iterativeCrawledKeywords
    # Form1 >>>>>>>>>>>>
    if request.method =='POST':
        form1 = SearchURL(request.POST)
        if form1.is_valid():
            iterativeCrawledKeywords = []
            url = form1.cleaned_data.get('url')
            pages = form1.cleaned_data.get('depth_url')
            if pages:
                depth = pages
            else:
                depth = 3

            messages.info(request, f'These are your results...')
            base_url = reverse('crawled')
            code = "surface_url"
            query_string =  urlencode({'url': url, 'depth':depth, 'code':code})
            url = '{}?{}'.format(base_url, query_string)
            return redirect(url)
    else:
        form1 = SearchURL()
    # <<<<<<<<<<<< Form1

    # Form2 >>>>>>>>>>>>
    if request.method =='POST':
        form2 = SearchKeywordPlt(request.POST)
        if form2.is_valid():
            iterativeCrawledKeywords = []
            keyword = form2.cleaned_data.get('keyword')
            platform = form2.cleaned_data.get('platform')
            pages = form2.cleaned_data.get('depth_key')
            isIterative = form2.cleaned_data.get('isIterative')
            if pages:
                depth = pages
            else:
                depth = 3 
            code = "surface_key"
            messages.info(request, f'These are your results...')
            base_url = reverse('crawled')
            query_string =  urlencode({'keyword': keyword, 'platform':platform, 'depth':depth,'isIterative':isIterative, 'code':code})
            url = '{}?{}'.format(base_url, query_string)
            return redirect(url)

    else:
        form2 = SearchKeywordPlt()
    # <<<<<<<<<<<< Form2

    return render(request, 'users/surface.html', {'form1':form1, 'form2':form2, 'title':"Surface web Crawl"})
 
     
@login_required
def dark(request):
    global iterativeCrawledKeywords
    # Form1 >>>>>>>>>>>>
    if request.method =='POST':
        form1 = SearchURL(request.POST)
        if form1.is_valid():
            iterativeCrawledKeywords = []
            url = form1.cleaned_data.get('url')
            pages = form1.cleaned_data.get('depth_url')
            if pages:
                depth = pages
            else:
                depth = 3
            code = "dark_url"
            messages.info(request, f'These are your results...')
            base_url = reverse('crawled')
            query_string =  urlencode({'url': url, 'depth':depth, 'code':code})
            url = '{}?{}'.format(base_url, query_string)
            return redirect(url)
    else:
        form1 = SearchURL()
    # <<<<<<<<<<<< Form1

    # Form2 >>>>>>>>>>>>
    if request.method =='POST':
        form2 = SearchKeyword(request.POST)
        if form2.is_valid():
            iterativeCrawledKeywords = []
            keyword = form2.cleaned_data.get('keyword')
            pages = form2.cleaned_data.get('depth_key')
            isIterative = form2.cleaned_data.get('isIterative')
            if pages:
                depth = pages
            else:
                depth = 3 
            code = "dark_key"
            messages.info(request, f'These are your results...')
            base_url = reverse('crawled')
            query_string =  urlencode({'keyword': keyword, 'depth':depth, 'isIterative':isIterative, 'code':code})
            url = '{}?{}'.format(base_url, query_string)
            return redirect(url)
    else:
        form2 = SearchKeyword()
    # <<<<<<<<<<<< Form2

    return render(request, 'users/dark.html', {'form1':form1, 'form2':form2, 'title':"Dark web Crawl"})

# Crawling thorugh URLs    
@login_required
def crawled(request):
    start_time = datetime.now()
    code = request.GET.get('code')
    isIterative = request.GET.get('isIterative') == "True"

    global database
    global collection 
    global iterativeCrawledKeywords
    global crawled_dropdown_choices

    if code == 'surface_url':
        url = request.GET.get('url')
        depth = int(request.GET.get('depth'))
        crawler = SurfaceURL(url, depth)
        links, topFiveWords = crawler.surfacecrawl()
        database = "surfacedb"
        collection = url
        data = {"Platform": "Surface URL", "Seed URL": url, "Depth":depth}

    if code == 'surface_key':
        keyword = request.GET.get('keyword')
        depth = int(request.GET.get('depth'))
        platform = int(request.GET.get('platform'))
        collection = keyword

        if isIterative:
            iterativeCrawledKeywords.append(keyword)
        else: 
            iterativeCrawledKeywords = []

        if platform == 1:
            ig = Instagram(keyword, depth)
            links, topFiveWords = ig.instacrawl()
            database = "instagramdb"
            data = {"Platform": "Instagram", "Keyword": keyword, "Depth":depth}
            
        if platform == 2:
            tweet = Twitter(keyword, depth)
            links, topFiveWords = tweet.twittercrawl()
            database = "twitterdb"
            data = {"Platform": "Twitter", "Keyword": keyword, "Depth":depth}

    if code == 'dark_url':
        url = request.GET.get('url')
        depth = int(request.GET.get('depth'))
        minicrawl = MiniCrawlbot()
        links, topFiveWords = minicrawl.tor_crawler(url, depth, False)
        database = "dark-url-db"
        collection = url
        data = {"Platform": "Dark Web URL", "Seed URL": url, "Depth":depth}

    if code == 'dark_key':
        keyword = request.GET.get('keyword')
        depth = int(request.GET.get('depth'))
        minicrawl = MiniCrawlbot()
        links, topFiveWords = minicrawl.tor_crawler(keyword, depth, True)
        database = "dark-key-db"
        collection = keyword
        data = {"Platform": "Dark Web Keyword", "Keyword": keyword, "Depth":depth}
        if isIterative:
            iterativeCrawledKeywords.append(keyword)
        else: 
            iterativeCrawledKeywords = []
        
    addhistory(request.user.username, data)

    end_time = datetime.now()
    diff = end_time - start_time
    time_elapsed = str(diff)[2:11]

    # Get next iteration
    full_path = request.get_full_path()
    urlSub1 = full_path.split("=", 1)[0] + "="
    urlSub2 = "&" + full_path.split("&", 1)[1]

    wordUrls = []
    for word in topFiveWords:
        wordUrls.append(word.replace(" ", "+"))

    topWords = zip(topFiveWords, wordUrls)

    if len(iterativeCrawledKeywords) == 5:
        isIterative = False
    
    if len(iterativeCrawledKeywords)>0:
        crawled_dropdown_choices = []
        count = 0
        for iterativeCrawledKeyword in iterativeCrawledKeywords:
            crawled_dropdown_choices.append((count, iterativeCrawledKeyword))
            count += 1
        crawled_dropdown_choices.append((count, "All words together"))


    return render(request, 'users/crawled.html', {'links':links, 'time_elapsed':time_elapsed, 'isIterative':isIterative, 'topWords':topWords, 'urlSub1':urlSub1, 'urlSub2':urlSub2, 'title':"Crawling reults"})
    

@login_required
def img_processing(request):
    links_images = get_images(database, collection)
    related_links = []
    for link_image in links_images:
        detected = False
        link, img_link = link_image
        print("Processing: ", link)
        if isinstance(img_link, str):
            detected = detect_object(img_link)
        elif isinstance(img_link, list):
            for img in img_link:
                detected = detect_object(img)
                if detected:
                    break
        if detected:
            related_links.append(link)

    return render(request, 'users/img_process.html', {'related_links':related_links, 'title':"Image Processing"})

@login_required
def text_processing(request):
    links_texts = get_text(database, collection)
    related_links = []
    for link_text in links_texts:
        detected = False
        link, text = link_text
        detected = detect_text(text)
        if detected:
            related_links.append(link)

    return render(request, 'users/text_process.html', {'related_links':related_links, 'title':"Text Processing"})