import logging

PLAYLIST_STRUCTURE = [   
	{
		"name": "Rekenen",
		"playlist": "Arithmetic"
	},	
	{
		"name": "Developmental Math",
		"playlist": "Developmental Math"
	},  
	{
		"name": "Developmental Math 2",
		"playlist": "Developmental Math 2"
	},  
	{
		"name": "Algebra",
		"playlist": "Algebra"
	},  
	{
		"name": "Pre-Algebra",
		"playlist": "Pre-Algebra"
	},
	{
		"name": "Taal",
		"playlist": "Taal"
	}
]

UNCATEGORIZED_PLAYLISTS = ['New and Noteworthy']

# Each DVD needs to stay under 4.4GB

DVDs_dict = {
    'Math': [ # 3.85GB
        'Arithmetic',
        'Pre-algebra',
        'Algebra',
        'Geometry',
        'Trigonometry',
        'Probability',
        'Statistics',
        'Precalculus',
    ],
    'Advanced Math': [ # 4.11GB
        'Calculus',
        'Differential Equations',
        'Linear Algebra',
    ],        
    'Math Worked Examples': [ # 3.92GB
        'Developmental Math',
        'Developmental Math 2',
        'Algebra I Worked Examples',
        'ck12.org Algebra 1 Examples',
        'Singapore Math',
    ],
    'Chemistry': [ # 2.92GB
        'Chemistry',
        'Organic Chemistry',
    ],
    'Science': [ # 3.24GB
        'Cosmology and Astronomy',
        'Biology',
        'Physics',
    ],
    'Finance': [ # 2.84GB
        'Finance',
        'Banking and Money',
        'Valuation and Investing',
        'Venture Capital and Capital Markets',
        'Credit Crisis',
        'Paulson Bailout',
        'Geithner Plan',
        'Current Economics',
        'Currency',
    ],
    'Test Prep': [ # 3.37GB
        'MA Tests for Education Licensure (MTEL) -Pre-Alg',
        'California Standards Test: Algebra I',
        'California Standards Test: Algebra II',
        'California Standards Test: Geometry',        
        'CAHSEE Example Problems',
        'SAT Preparation',
        'IIT JEE Questions',
        'GMAT: Problem Solving',
        'GMAT Data Sufficiency',        
    ],
    'Misc': [ # 1.93GB
        'Talks and Interviews',
        'History',   
        'Brain Teasers',
    ],    
}

# replace None with the DVD name above that you want to burn
# this will restrict the homepage to only show the playlists from that list
DVD_list = DVDs_dict.get(None) #'Math'

def sorted_playlist_titles():
    playlist_titles = []
    append_playlist_titles(playlist_titles, PLAYLIST_STRUCTURE)
    playlist_titles.extend(UNCATEGORIZED_PLAYLISTS)
    return sorted(set(playlist_titles))

def append_playlist_titles(playlist_titles, obj):
    type_obj = type(obj)
    if type_obj == dict:
        if obj.has_key("items"):
            append_playlist_titles(playlist_titles, obj["items"])
        else:
            playlist_titles.append(obj["playlist"])
    elif type_obj == list:
        for val in obj:
            append_playlist_titles(playlist_titles, val)

if DVD_list:
    topics_list = all_topics_list = DVD_list
else:
    topics_list = all_topics_list = sorted_playlist_titles()

