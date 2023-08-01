import multiprocessing as mp
import queue, requests, os, re, pickle
from threading import Thread
from bs4 import BeautifulSoup
from tqdm import tqdm

def pickle_save(obj, path):
    with open(path, 'wb') as pkl:
        pickle.dump(obj, pkl)

def pickle_load(path):
    with open(path, 'rb') as pkl:
        return pickle.load(pkl)

class Process(Thread):
    def __init__(self, q, func, args):
        Thread.__init__(self)
        self.queue = q
        self.func = func
        self.args = args
        self.results = []
    def run(self):
        while True:
            item = self.queue.get()
            if item is None:
                break
            self.results.append(self.func(item, *self.args))
            self.queue.task_done()

def map_parallel(iterable, func, args=list(), no_workers=mp.cpu_count()):
    # queue with addresses
    q = queue.Queue()
    for item in iterable:
        q.put(item)
    # workers into the queue
    workers = [Process(q, func, args) for _ in range(no_workers)]
    for worker in workers:
        worker.start()
    # add the None item to each worker's queue to trigger stopping
    for _ in workers:
        q.put(None)
    # join workers - wait till they have finished
    for worker in workers:
        worker.join()
    # combine all worker results
    r = []
    for worker in workers:
        r.extend(worker.results)
    return r

def download_case(payload, hdr={'User-Agent': 'Bob'}):
    case_url, dest_path = payload
    try:
        # Download the page
        response = requests.get(case_url, headers=hdr)
        # Parse the html
        soup = BeautifulSoup(response.content)
        # Find the title
        title = soup.find("div", {"id":"page-main"}).find_all('h1')[0]
        # Trim off superfluous details
        title = title.contents[0].split(';')[0] 
        # Remove non-alphanum chars
        title = re.sub("[^a-zA-Z0-9 -]", "", title) 
        # Replace spaces with underscore
        title = re.sub(" ","_", title)
        # Generate a convenient filename from the URL
        tokens = case_url.split('/')[-2:]
        tokens[1] = tokens[1].split('.')[0]
        filename = '_'.join(tokens)
        obj = {'title': title, 'url': case_url, 'response': response}
        save_path = os.path.join(dest_path, f'{filename}.pkl')
        # Save
        pickle_save(obj, save_path)
    except:
        # Download failed for some internetty reason. Return fails for re-try.
        return (case_url, dest_path)
    

def main(max_retries=5):

    root = os.path.join('data','output','cases')
    jurisdictions = os.listdir(root)
    hdr = {'User-Agent': 'Bob'}

    for jurisdiction in jurisdictions:

        jurisdiction_path = os.path.join(root, jurisdiction)
        courts = os.listdir(jurisdiction_path)

        for court in courts:
            
            # Remembering which cases we have already downloaded
            court_path = os.path.join(jurisdiction_path, court)
            cases = os.listdir(court_path)

            case_objs = [pickle_load(os.path.join(court_path, case)) for case in cases]
            saved_urls = [obj['url'] for obj in case_objs]

            print(f'{jurisdiction} - {court} cases already saved: {len(saved_urls)}')
            print(f'Parsing website for new cases...')

            court_url = f"http://www.austlii.edu.au/cgi-bin/viewdb/au/cases/{jurisdiction}/{court}/"
            response = requests.get(court_url, headers=hdr)
            soup = BeautifulSoup(response.content)

            year_hrefs = soup.find("div", {"class": "year-options-list"}).find_all('a', href=True)
            years = sorted(set.union(*[set(re.findall('[0-9]{4}', str(r))) for r in year_hrefs]))

            for year in tqdm(years):

                court_year_url = f'http://www.austlii.edu.au/cgi-bin/viewtoc/au/cases/{jurisdiction}/{court}/{year}/'
                response = requests.get(court_year_url, headers=hdr)
                soup = BeautifulSoup(response.content)

                links = [link['href'] for link in soup.find_all('a', href=True)]
                case_links = [l for l in links if re.search(f'{year}/[0-9]+.html', l)]
                case_urls = [f'http://www.austlii.edu.au{link}' for link in case_links]

                # Cases not yet saved
                new_case_urls = [url for url in case_urls if url not in saved_urls]
                payloads = [(url, court_path) for url in new_case_urls]
                
                # Hit up each case and download the response.
                fails = map_parallel(payloads, download_case, no_workers=8)
                fails = [f for f in fails if f]
        
    retries = 1
    while retries <= max_retries and len(fails) > 0:

        # Second attempt at downloading failed cases.
        print(f'Retry attempt {retries} at {len(fails)} failed downloads.')
        fails = map_parallel(fails, download_case, no_workers=8)
        fails = [f for f in fails if f]

        # Final report
        print(f'Cases still failed: {len(fails)}')
        retries += 1

    if len(fails) > 0:
        print(f'I failed you sir, on {len(fails)} urls.')
    else:
        print('Corpus obtained sir.')

if __name__ == "__main__":
    main()