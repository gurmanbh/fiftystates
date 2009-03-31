#!/usr/bin/env python
import urllib2
import re
import datetime as dt
#beautiful soup dies on the bill summary page, switching to lxml
#from BeautifulSoup import BeautifulSoup
from lxml.html import parse

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

class WALegislationScraper(LegislationScraper):

    state = 'wa'

    def scrape(self, year):
      
        # get bills by topic search page -- gives a list of bill IDs per year
        bills_url = 'http://apps.leg.wa.gov/billsbytopic/default.aspx?year=%s' % (year)
        print bills_url
        bills = parse(bills_url).getroot()
        for option in bills.cssselect('select#ucDefault_talCriteria option'):
            number = option.text
                 
            #get bill summary
            summary_url = 'http://dlr.leg.wa.gov/billsummary/default.aspx?Bill=%s&year=%s' % (number, year)
            print summary_url
            summary = parse(summary_url).getroot()
            
            #TODO, this doesn't work for 2005
            
            if summary.cssselect('span#ctl00_contentRegion_lblShortBillID')[0].text.startswith('HB'):
                chamber = "lower"
            else:
                chamber = "upper"
            session = year #correct??
            title = summary.cssselect('span#ctl00_contentRegion_lblBriefDescription')[0].text
            self.add_bill(chamber, session, number, title)
            
            #get bill versions
            versions = summary.cssselect('td[style*="dashed"] a[href*="/Pdf/Bills"]')
            for version in versions:
                self.add_bill_version(chamber, session, number, version.text, version.get('href'))
                
            sponsors = summary.cssselect('td:contains("Sponsors:") span.ObviousLink a')               
            for sponsor in sponsors:
                self.add_sponsorship(chamber, session, number, 'cosponsor', sponsor.text)
                       
            #TODO: amendments -- new thing? -- isamendment field on version
            #TODO: new csv, not in core, fiscal_notes
            #TODO: extra field on action for the bill version link
            
            
            #the dates are incomplete on the web page we're scraping
            #so we must match the page w/ the rss feed to get all the goods
            #the rss feed doesn't have the chamber for the actions, so we scrape that from the page
            page_actions = []
            action_chamber = chamber #start with the originating chamber
            for x in summary.cssselect('tr#ctl00_contentRegion_trPlaceHolder>td>table>tr'):
                y = x.cssselect('td[colspan="3"] b')
                if len(y) > 0:
                    header = y[0].text
                    print header
                    #grab the action chamber and hang on to it until it changes
                    #TODO: find an example where it changes and test
                    if header.endswith("SENATE"):
                        action_chamber = 'upper'
                    if header.endswith("HOUSE"):
                        action_chamber = 'lower'
                z = x.cssselect('td[width="100%"]')
                if len(z) > 0:
                    #clip out the links to other stuff
                    links = z[0].cssselect('span.HistoryLink')
                    for link in links:
                        z[0].remove(link)
                    act = z[0].text_content().strip().rstrip('.')
                    print act
                    page_actions.append([act,action_chamber])

            #reverse to match up w/ order of feed
            page_actions.reverse()

            #testing mocks
#            chamber = 'lower'
#            year = '2009'
#            number = '1004'
#            session = '2009'
#            test = []

            actions_feed_url = 'http://apps.leg.wa.gov/billinfo/summaryrss.aspx?year=%s&bill=%s' % (year, number)
            print actions_feed_url
            actions_feed = parse(actions_feed_url).getroot()
            actions = actions_feed.cssselect('item title')
            i = 0
            for action in actions:
                print action.text
                action_split = action.text.split(' - ')
                action_date = action_split[1]
                action_desc = action_split[2]
                action_chamber = page_actions[i][1]
                i += 1
                self.add_action(chamber, session, number, action_chamber, action_desc, action_date)                
            
            #debug
            break

#        for link in links:
#            bill_number = link.contents[0]
#            bill_id = bill_abbr + 'B' + bill_number
#            print "Getting %s" % bill_id

#            # Get info page
#            info_url = 'http://www.legis.state.pa.us/cfdocs/billinfo/billinfo.cfm?syear=%s&sind=%i&body=%s&type=B&BN=%s' % (y1, session_num, bill_abbr, bill_number)
#            info_page = BeautifulSoup(urllib2.urlopen(info_url).read())

#            # Get bill title
#            title_label = info_page.find(text='Short Title:')
#            bill_title = title_label.findNext().string

#            # Add bill
#            self.add_bill(chamber, session, bill_id, bill_title)

#            # Get bill versions
#            pn_table = info_page.find('div', {"class": 'pn_table'})
#            text_rows = pn_table.findAll('tr')[1:]
#            for tr in text_rows:
#                text_link = tr.td.a
#                text_url = 'http://www.legis.state.pa.us%s' % text_link['href']
#                self.add_bill_version(chamber, session, bill_id,
#                                      text_link.string, text_url)

#            # Get bill history page
#            history_url = 'http://www.legis.state.pa.us/cfdocs/billinfo/bill_history.cfm?syear=%s&sind=%i&body=%s&type=B&BN=%s' % (y1, session_num, bill_abbr, bill_number)
#            history = BeautifulSoup(urllib2.urlopen(history_url).read())

#            # Get sponsors
#            # (format changed in 2009)
#            if int(year) < 2009:
#                sponsors = history.find(text='Sponsors:').parent.findNext('td').find('td').string.strip().replace(' and', ',').split(', ')
#                self.add_sponsorship(chamber, session, bill_id, 'primary',
#                                 sponsors[0])
#                for sponsor in sponsors[1:]:
#                    self.add_sponsorship(chamber, session, bill_id, 'cosponsor',
#                                         sponsor)
#            else:
#                sponsors = history.find(text='Sponsors:').parent.findNext().findAll('a')
#                self.add_sponsorship(chamber, session, bill_id, 'primary',
#                                     sponsors[0].string)
#                for sponsor in sponsors[1:]:
#                    self.add_sponsorship(chamber, session, bill_id, 'cosponsor',
#                                         sponsor.string)

#            # Get actions
#            act_table = history.find(text="Actions:").parent.findNextSibling()
#            act_chamber = chamber
#            for row in act_table.findAll('tr'):
#                act_raw = row.td.div.string.replace('&#160;', ' ')
#                act_match = re.match('(.*),\s+((\w+\.?) (\d+), (\d{4}))', act_raw)
#                if act_match:
#                    self.add_action(chamber, session, bill_id, act_chamber,
#                                    act_match.group(1),
#                                    act_match.group(2).strip())
#                else:
#                    # Handle actions from the other chamber
#                    # ("In the (House|Senate)" row followed by actions that
#                    # took place in that chamber)
#                    cham_match = re.match('In the (House|Senate)', act_raw)
#                    if not cham_match:
#                        # Ignore?
#                        continue

#                    if cham_match.group(1) == 'House':
#                        act_chamber = 'lower'
#                    else:
#                        act_chamber = 'upper'


    def scrape_bills(self, chamber, year):
        # Data available from 1969 on
        if int(year) < 1969 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)
        
        # Expect first year of session (odd)
        if int(year) % 2 != 1:
            raise NoDataForYear(year)
    
        #ignoring lower, getting both chambers on upper -- easier to scrape both at once    
        if chamber == "upper":
            self.scrape(year)
            


if __name__ == '__main__':
    WALegislationScraper().run()
