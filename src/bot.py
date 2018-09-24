import pytumblr, tumblr, reddit, time, re, ConfigParser
from datetime import datetime

config = ConfigParser.RawConfigParser()
config.read('settings.cfg')

# Authenticate via OAuth
client = pytumblr.TumblrRestClient(
    config.get('tumblr', 'consumerKey'),
    config.get('tumblr', 'consumerSecret'),
    config.get('tumblr', 'oauthToken'),
    config.get('tumblr', 'oauthSecret')
)

# Make the request
client.info()

class Bot():
    def __init__(self, subreddit, queryType = 'hot', limit = 20, timer = 3600):
        self.redditAPI = reddit.API()
        self.tumblrAPI = tumblr.API()
        self.subreddit = subreddit
        self.timer = timer
        self.queryType = queryType.lower()
        self.limit = limit
        self.latest = None

    # get latest posts from specified subreddit via reddit API
    def getLatestRedditPosts(self):
        posts = self.redditAPI.getPosts(subreddit=self.subreddit,limit = self.limit, queryType = self.queryType, after=self.latest)

        # update self.latest for later paginated queries
        if(len(posts) > 0):
            self.latest = "t3_" + str(posts[-1].id)
        return posts

    # pull necessary information from reddit posts
    def getFormattedRedditPosts(self):
        redditPosts = self.getLatestRedditPosts()
        formattedPosts = []

        for post in (x for x in redditPosts if x is not None):
            formattedPost = {}

            # only parse and save post if it isn't a self post
            if(not re.search('!reddit.com', post.url.lower(), re.IGNORECASE)):
                formattedPost['url'] = post.url
                formattedPost['permalink'] = post.permalink
                formattedPost['score'] = post.score
                formattedPost['title'] = post.title

                timeDiff = datetime.utcfromtimestamp(time.time() - post.created_utc).hour
		minAge = config.get('reddit','minAge')
		maxAge = config.get('reddit','maxAge')
		minScore = config.get('reddit','minScore')

                if(timeDiff > int(minAge) and timeDiff < int(maxAge) and post.score > int(minScore)):
                    formattedPosts.append(formattedPost)
        return formattedPosts

    # create Tumblr posts for all retrieved reddit posts
    def createTumblrPosts(self, redditPosts):
        for post in redditPosts:
            caption = "<h2><a href=\"" + post['permalink'] + "\">" + post['title'] + "</a></h2>"

            client.create_photo(config.get('tumblr', 'blogName'), state='queue', tags=post['title'].split(), caption=caption, source=post['url'])

    # query for reddit posts and subsequently create Tumblr posts
    def process(self):
        redditPosts = self.getFormattedRedditPosts()
        if(len(redditPosts) > 0):
            self.createTumblrPosts(redditPosts)

    def run(self):
        cycleCount = 0
        while True:
            # start from beginning every 12 hours if we're retrieving 'hot' posts
            if(self.queryType.lower() == 'hot'):
                if(cycleCount == 12):
                    self.latest = None
                    cycleCount = 0
                cycleCount += 1
            self.process()
            time.sleep(self.timer)
