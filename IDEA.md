Our goal is to create a simple crawler / parser that will verify the best SEO practices on a given site. We will start with more basic things, like simply verifying that everything is online and responds correctly. Then we will go into basic HTML checkups.

# Definitions
- Page ID: defined as the http code plus url slug https://example.com/blog-post-1234 -> 200-blog-post-1234, https://example.com/contact/form-123 -> 200-form-123 in folder `contact`. So it's `$HTTP_CODE-$URL_SLUG.html`, placed in the nested folders if necessary. If the page has 400s or 500s codes record them too. We want to count them afterwards. Also save any 300s redirects.
- Website ID: defined as the domain name + TLD, https://example.com -> example_com. This will be used as the root folder where all scraped HTMLs are downloaded.



# 1 - Scraper Script

### Requirements:
- Must support HTTP Auth
- Must mimic real user browser (user agent, headers etc)
- Keep track of which pages were already downloaded to avoid sending the same request twice
- Parallelization, fetching up to 20 pages in parallel. Without race connditions and without messing up the tracking logic.

### Flow:
1) We will have website URL and maximum amount of pages to fetch (default = 100) hardcoded in the beginning of the script. Http auth will be hardcoded here as well, as two fields - username & password.
2) Creates (or scan the existing one) a folder where the scraped pages will be saved. If already exists - load into memory all the pages that were already downloaded in previous runs. Can be rerun multiple times to refetch missing pages in this manner. Download the sitemap xml files and robots txt.
3) Start with sitemap, go over it and download each page from the sitemap.
4) Continue with internal links, go over each downloaded page and fetch all the internal links from it (only previously unseen ones).
5) Debug the stats of this scraping session at the end.



# 2 - Sitemap.xml Checker

### Requirements:
- Must support HTTP Auth
- Must mimic real user browser (user agent, headers etc)
- Must support basic .xml for now, but we will need to implement archieved sitemaps support soon too

### Flow:
1) We will have the website URL hardcoded in the beginning of the script.
2) Go over the sitemap, check every page that we downloaded from it. Highlight and exit immediately if not the full sitemap was downloaded. Go over each image if the sitemap has them and download them as well. Include them as a separate point in the overall statistics
3) Show the statistics, how many pages are 200s, how many are 300s, or 400s, or 500s. Highlight the errors and redirects. Show full debug of the sitemap.



# 3 - Page Checker

The main goal is to easily debug and verify all the main elements of a single HTML page and make sure everything follows the best SEO practices.

### Flow
1) Check H1/H2 titles. Only one H1 per page.
2) Check all internal links on this page, and their response codes, and the keywords.
3) Check all external links on this page, and their response codes, and the keywords.
4) Check page title and other SEO related things (TODO: expand on this)
5) Check images, their links, their response codes, their alt texts.



# 4 - Wayback Machine Scraper

A tool that will scrape website snapshots from the web.archive.org site, our main goal is to use it for competitors analysis, to see how their websites were changing.

### Flow
1) We will have the website URL hardcoded in the beginning of the script. 
2) We will download all snapshot list jsons from the http://web.archive.org/cdx/search/cdx, going back to the first recorded snapshot, and save these jsons to the folder. The folder will be the "$WEBSITE_ID_archive" folder.   
3) We will have the frequency of snapshot downloads hardcoded in the beginning of the script. Daily, weekly, monthly. We will try to download HTMLs from snapshots with this frequency. So only 1 per day, 1 per week, 1 per month. Pick a middle point.   
4) Frequency downloads of HTML should be handled by first parsing the timestamps and distributing the snapshots along a timeline.



# 5 - Page Check Results Comparisons

