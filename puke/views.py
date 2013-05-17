from django.conf import settings
from django.shortcuts import render_to_response
import imaplib
import os
import re
import requests
from BeautifulSoup import BeautifulSoup
from launchpadlib.launchpad import Launchpad
import urlparse

def create_wi_list(text):
    work_items = []
    valid_states = ["TODO", "INPROGRESS", "POSTPONED"]  # "DONE" is left out - don't care about it!

    for line in text.splitlines():
        match = re.search("^(.*?)\\s*:\\s*(\\w+)\\s*$", line)
        if match and match.group(2) in valid_states:
            work_items.append((match.group(1), match.group(2)))

    return work_items

def home(request):
    # Email
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(settings.GMAIL_USER, settings.GMAIL_PASSWORD)
    mail.select("inbox") # connect to inbox.
    result, data = mail.uid("search", None, "UnSeen")
    if len(data[0]):
        result, data = mail.uid('fetch', ",".join(data[0].split()),
                '(BODY.PEEK[HEADER.FIELDS (SUBJECT)] X-GM-THRID X-GM-MSGID)')
    threads = {}

    for thing in data:
        if len(thing) == 2:
            mail_id = hex(int(re.search(r"X-GM-THRID\s+(\d+)", thing[0]).group(1)))
            threads[mail_id] = (re.sub(r"[\n\r]", "", thing[1]),
                "https://mail.google.com/mail/u/0/?shva=1#inbox/" + mail_id[2:])

    # Launchpad login
    cachedir = os.path.join(settings.PROJECT_ROOT, ".launchpadlib/cache/")
    launchpad = Launchpad.login_anonymously('just testing', 'production', cachedir)
    me = launchpad.people[settings.LP_USER]

    # Bugs
    lp_bugs = []
    for bug in me.searchTasks(assignee=me):
        lp_bugs.append({
            "title": re.search('"(.*)"', bug.title).group(1),
            "url": bug.web_link,
            "target": bug.bug_target_display_name,
            "importance": bug.importance,
            "status": bug.status
        })

    bug_prio = {
        "Undecided": 0,
        "Critical": 1,
        "High": 2,
        "Medium": 3,
        "Low": 4,
        "Wishlist": 5,
    }

    lp_bugs = sorted(lp_bugs, key=lambda bug: bug_prio[bug["importance"]])

    # Reviews
    reviews = []
    for review in me.getRequestedReviews():
        reviews.append(review.web_link)

    merge_proposals = []
    for mp in me.getMergeProposals():
        merge_proposals.append(mp.web_link)

    # Blueprints
    r = requests.get("https://blueprints.launchpad.net/~%s/+specs?role=assignee" % settings.LP_USER)
    soup = BeautifulSoup(r.text)
    junk = soup.findAll("span", {"class": "sortkey"})
    [thing.extract() for thing in junk]

    links = soup.findAll("a")
    bp_links = []
    for link in links:
        if not re.search("/\+spec/", link["href"]):
            continue
        if not re.search("^http", link["href"]):
            link["href"] = urlparse.urljoin("https://blueprints.launchpad.net",
                                            link["href"])
            bp_links.append(link["href"])

    lp_blueprints = []
    seen_links = {}
    for link in bp_links:
        if link in seen_links:
            continue
        else:
            seen_links[link] = True

        bp = requests.get(re.sub(r"https://blueprints.launchpad.net",
                            r"https://api.launchpad.net/devel", link)).json

        if(bp["assignee_link"] ==
            "https://api.launchpad.net/devel/~%s" % settings.LP_USER and
           link not in settings.IGNORE["lp_bp"]):
            lp_blueprints.append({
                "url": link,
                "name": bp["title"],
                "priority": bp["priority"],
                "definition_status": bp["definition_status"],
                "implementation_status": bp["implementation_status"],
                "work_items": create_wi_list(bp["workitems_text"]),
            })

    # Cards
    jira_cards = requests.get(
        "http://cards.linaro.org/rest/api/2/search?jql=assignee=%s" %
        settings.JIRA_LOGIN[0], auth=settings.JIRA_LOGIN)

    cards = []
    for issue in jira_cards.json["issues"]:
        cards.append({
            "name": issue["fields"]["summary"],
            "url": "http://cards.linaro.org/browse/" + issue["key"],
            "status": issue["fields"]["status"]["name"],
            "priority": issue["fields"]["priority"]["name"],
            "fix_versions": " ".join([v["name"] for v in issue["fields"]["fixVersions"]])
        })

    return render_to_response('home.html',
        {
            "lp_bp": lp_blueprints,
            "lp_bugs": lp_bugs,
            "jira_cards": cards,
            "reviews": reviews,
            "merge_proposals": merge_proposals,
            "emails": threads
        })
