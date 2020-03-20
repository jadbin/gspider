# coding=utf-8

from gspider import Spider, HttpRequest, run_spider, Selector


class BaiduNewsSpider(Spider):
    def start_requests(self):
        yield HttpRequest("http://news.baidu.com/")

    def parse(self, response):
        selector = Selector(response.text)
        hot = selector.css("div.hotnews a").text
        self.log("Hot News:")
        for i in range(len(hot)):
            self.log("%s: %s", i + 1, hot[i])


if __name__ == '__main__':
    run_spider(BaiduNewsSpider)
