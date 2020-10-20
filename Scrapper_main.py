from requests_html import HTMLSession
import math
from urllib.parse import urljoin
import pickle
import pandas as pd


def get_vote_pages():
    NewSaeima.scrap_calendar_page()
    NewSaeima.find_links_in_calendar_page()
    NewSaeima.scrap_day_pages()
    NewSaeima.find_links_in_days_pages()
    NewSaeima.scrap_vote_pages()


def find_subject(string):
    # Finds Subject string in Voting page
    start_cond = 'Balsošanas motīvs: </span><b>'
    end_cond = '</b>'
    return find_in_string(string, start_cond, end_cond)[0]


def find_date(string):
    # Finds Date of voting in Voting page
    start_cond = 'Datums: </span><b>'
    end_cond = '</b>'
    return find_in_string(string, start_cond, end_cond)[0]


def split_row_to_data(input_string):
    # Voting row consists of two cells, this returns tulpe of two cells separated
    entry1, idx = find_in_string(input_string, '<td>', '<td class="emptyCell">\xa0</td>')
    entry2, idx = find_in_string(input_string, '<td class="emptyCell">\xa0</td>', '</tr>')
    if entry1:
        entry1 += '<td>'
    return entry1, entry2


def extract_vote_data(input_string):
    # Extracts vote data from a cell that begins with <td> and ends with </td>
    # input format is is <td>id</td><td>name</td><td>party</td><td>vote</td>
    # returns id,name,party,vote
    end = [0, 0, 0, 0]
    num, end[0] = find_in_string(input_string, '<td>', '</td>')
    name, end[1] = find_in_string(input_string[(end[0]):], '<td>', '</td>')
    end[1] += end[0]
    party, end[2] = find_in_string(input_string[end[1]:], '<td>', '</td>')
    end[2] += end[1]
    vote, end[3] = find_in_string(input_string[end[2]:], '<td>', '</td>')
    return num, name, party, vote


class Saeima:
    def __init__(self):
        self.scrapped_voting_pages = []
        self.voting_links = []
        self.scrapped_day_pages = []
        self.scrapped_calendar_page = 0
        self.links_in_calendarHolder = []
        self.urls = []

    def scrap_calendar_page(self):
        print('Getting calendar page')
        session = HTMLSession()
        r = session.get('http://titania.saeima.lv/LIVS13/SaeimaLIVS2_DK.nsf/DK?ReadForm&calendar=1')
        print('Rendering calendar page')
        r.html.render(timeout=80000)  # this call executes the js in the page
        self.scrapped_calendar_page = r
        session.close()

    def find_links_in_calendar_page(self):

        print('Collection session days urls')
        calendar_holder = self.scrapped_calendar_page.html.find('.calendarHolder')[0]
        self.links_in_calendarHolder = calendar_holder.absolute_links

    def scrap_day_pages(self):
        print('Getting session day pages ')

        session = HTMLSession()
        print('Total Day pages to get', len(self.links_in_calendarHolder))
        for ch_idx, s_url in enumerate(self.links_in_calendarHolder):
            percent = math.floor(ch_idx * 100 / len(self.links_in_calendarHolder))
            print(percent, '%', end='\r')
            t = session.get(s_url)
            t.html.render(timeout=80000)
            self.scrapped_day_pages.append(t)
        session.close()
        print('done!')

    def find_links_in_days_pages(self):
        print('find_links_in_day_pages')
        for d_idx, day in enumerate(self.scrapped_day_pages):
            percent = math.floor(d_idx * 100 / len(self.scrapped_day_pages))
            print(percent, '%', end='\r')

            voting_link_containers = day.html.find('span', containing='balsojums')
            str_start = 0
            is_url = False
            check_links_in_day_string = "window.open('./0/"
            for v_link_container in voting_link_containers:
                for c_idx, char in enumerate(v_link_container.html):
                    if (char == '/') and is_url is False:
                        string_test = v_link_container.html[c_idx - len(check_links_in_day_string) + 1: c_idx + 1]
                        # print(string_test)
                        if string_test == check_links_in_day_string:
                            str_start = c_idx - 3
                            is_url = True
                    if char == ',' and is_url is True:
                        str_end = c_idx - 1
                        # print('got balsojuma url:', v_link_container.html[str_start:str_end])
                        url = urljoin(day.url, v_link_container.html[str_start:str_end])
                        self.voting_links.append(url)
                        is_url = False
                        break

        print('done!')

    def scrap_vote_pages(self):
        print('getting vote pages rendered')
        session = HTMLSession()
        for sv_idx, link in enumerate(self.voting_links):
            percent = math.floor(sv_idx * 100 / len(self.voting_links))
            print(percent, '%', end='\r')

            r = session.get(link)
            r.html.render()
            self.scrapped_voting_pages.append(r)
        session.close()

    # def add_voting_list(self):
    #     for scrapped_voting in self.scrapped_votings:
    #         header=scrapped_voting.html.find('div .formHead2')
    #         deputies = scrapped_voting.html.find('tr .c1')
    #         self.voting_links.append(Voting(header[0][7:]),header[1][19:])

    def load_calendar_cache(self):
        with open('calendar_urls_cache', 'rb') as fp:
            self.urls = pickle.load(fp)

    def save_calendar_cache(self):
        if self.urls:
            with open('calendar_urls_cache', 'wb') as fp:
                pickle.dump(self.urls, fp)
        else:
            print("Error: self.urls is empty!")

    def validate_calendar_cache(self):
        result = True
        with open('calendar_urls_cache', 'rb') as fp:
            pick = pickle.load(fp)
        cache = pick
        for vc_idx, url in enumerate(self.urls):
            if str(url) != cache[vc_idx]:
                result = False
        if not result:
            print("Cached list is not corresponding!")
        else:
            print("Cache validated and is OK")
        return result


def find_in_string(input_string, start_cond, end_cond):
    # takes three strings - input_string, start_cond and end_cond
    # returns input_string located between start_cond string and end_cond strings
    # return format (string, first_char_idx)
    # returns 0,0 if string was not found
    is_legit = False
    str_start = 0
    for c_idx, char in enumerate(input_string):
        if (char == start_cond[-1]) and is_legit is False:
            string_test = input_string[c_idx - len(start_cond) + 1: c_idx + 1]
            # print(string_test)
            if string_test == start_cond:
                str_start = c_idx + 1
                is_legit = True
        if char == end_cond[-1] and is_legit:
            string_test = input_string[c_idx - len(end_cond) + 1: c_idx + 1]
            if string_test == end_cond:
                str_end = c_idx - len(end_cond) + 1
                return input_string[str_start:str_end], str_end
    return 0, 0


NewSaeima = Saeima()
get_vote_pages()

# This will create string: ['1.','2.'...'999.'
# We need it to verify that entries receieved from voting table is an actual vote
# If this data is missing from entry - hence data is not a legit vote (table is not perfect)
idx = 0
id_check_string = []
while idx < 1000:
    idx += 1
    string = str(idx) + '.'
    id_check_string.append(string)

votes = []

# for each vote page we scrapped
# we need to get each row in the table
# split it into two cells
# verify that cell is vote
# and write it to the vote list
for idx, voting_session in enumerate(NewSaeima.scrapped_voting_pages):

    percent = math.floor(idx * 100 / len(NewSaeima.scrapped_voting_pages))
    print(percent, '%', end='\r')

    header = voting_session.html.find('div .formHead2')
    subject_string = header[1].html
    date_string = header[0].html

    Date = find_date(date_string)
    Subject = find_subject(subject_string)

    rows = voting_session.html.find('tr .c1')
    for row in rows:
        entry1, entry2 = split_row_to_data(row.html)

        if entry1:
            Data1_ext = extract_vote_data(entry1)
            if Data1_ext[0] in id_check_string:
                # vote = Vote(Date,Subject,Data1_ext[1], Data1_ext[2],Data1_ext[3])
                votes.append(
                    {
                        'Date': Date,
                        'Subject': Subject,
                        'Name': Data1_ext[1],
                        'Party': Data1_ext[2],
                        'Vote': Data1_ext[3]
                    }
                )
        if entry2:
            Data2_ext = extract_vote_data(entry2)
            if Data2_ext[0] in id_check_string:
                # vote = Vote(Date, Subject, Data2_ext[1], Data2_ext[2], Data2_ext[3])
                votes.append(
                    {
                        'Date': Date,
                        'Subject': Subject,
                        'Name': Data2_ext[1],
                        'Party': Data2_ext[2],
                        'Vote': Data2_ext[3]
                    }
                )

df = pd.DataFrame(votes)
df.to_csv(r'Votes13Saeima.csv')

print('DONE!')
