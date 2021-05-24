##imports for plotting visuals
import pandas as pd
import dateutil.parser
import matplotlib.pyplot as plt
import matplotlib.colors as mc
import colorsys
import seaborn as sns
from numpy import insert
import numpy as np
import re



## class containing functions that visualize analytics across data gathered via social media platforms
class Visualize:
    
    def __init__ (self, db_obj, platform_db_name):
        self.db = db_obj
        self.dbName = platform_db_name
        self.dateStr = '2019-06-01T00:00:00.00Z' 
        self.timeFrameStart = dateutil.parser.parse(self.dateStr)
    
    
    ## for iNaturalist - get two lists of times from when posts are observed and when
    ## posts are upload for visualization
    def getObservedCreatedTimes(self, wild_col, observed_tf_start):
        
        # find documents observed from June 01 2019 - present
        observed_tf_start = dateutil.parser.parse(observed_tf_start)
        res = self.db[wild_col].find({'time_observed_utc': {'$gte': observed_tf_start}})
        
        obs_times =[]
        created_times =[]
        
        #retrieve times each encounter was observed and created 
        for doc in res:
            obs_times.append(doc['time_observed_utc'])
            created_times.append(doc['created_on'])
        return obs_times, created_times
    
    
    ## visualize the delay in time from an iNaturalist encounter occurs and when the post documenting the 
    ## encounter is uploaded/created
    def plotObservedCreatedDelays(self, wild_col, observed_tf_start="2019-06-01 00:00:00"):
        
        #create df with observed times and creation times
        observed_on_times, created_on_times= self.getObservedCreatedTimes(wild_col,observed_tf_start)
        df = pd.DataFrame({"observed_on": observed_on_times,"created_on": created_on_times})
        
        #find time delays - keep difference in days only
        time_delay = df["created_on"] - df["observed_on"]
        time_delay_days=[]
        for x in range(0, len(time_delay)):
            time_delay_days.append(time_delay[x].days)
        
        ##add column with time delay in days to dataframe for comparison/visualization
        df["time_delay_days"] = time_delay_days
        
        #plot date observed vs date uploaded in scatterplot
        fig, ax = plt.subplots(figsize=(14,14))
        sns.scatterplot(data=df, x="observed_on", y="created_on", hue="time_delay_days", palette='nipy_spectral', ax=ax)
        
        #plot a complementary histogram to visualize COUNTS
        delays = df['time_delay_days']
        plt.figure(figsize=(14,14))
        sns.histplot(data=df, x='time_delay_days')

        return df  

    
    ## function to print out info regarding volume of relevant/irrelevant posts
    def showNumDocsRelevant(self, collection):
        
        ## get total number of docs filtered through in collection
        total = self.db[collection].count_documents({ "$and": [{"relevant":{"$in":[True,False]}}]})
        if total == 0:
            print("No videos were processed yet.")
            return
        
        ## number of docs marked as relevant stored in our collection
        relevant_count = self.db[collection].count_documents({ "$and": [{"relevant":True}]})
        print("relevant: {} \n".format(relevant_count))
        
        ## percent relevant caluclated out of total
        relevant = self.db[collection].count_documents({ "$and": [{"relevant":True}]}) / total * 100 
        
        ## percent wild calculated out of ONLY relevant items, this way the remaining percent can be
        ## assumed to be % of zoo sightings
        try:
            wild = self.db[collection].count_documents({ "$and": [{"relevant":{"$in":[True]}}, {"wild":True}] }) / relevant_count * 100
            # percent wild calculated out of total
            wild_tot = self.db[collection].count_documents({ "$and": [{"relevant":{"$in":[True]}}, {"wild":True}] }) / total * 100
            print(" Out of {} items, {}% are relevant.From those that are relevant, {}% are wild. Out of the total, {}% are wild ".format(total, round(relevant,1), round(wild,1), round(wild_tot, 1)))
        
        except ZeroDivisionError:
            print("No wild documents in collection so far")
    
    
    ## function handling building the histogram to display time delay between successive posts
    ## only posts within the time frame are considered
    def showSuccessivePostsDelay(self, collection):
        
        ## time of encounter keywords across different platforms
        keys = {'youtube': 'publishedAt', 'twitter': 'created_at', 'iNaturalist': 'time_observed_utc', 
                'flickr_june_2019': 'datetaken'}

        ## gather wild encounter docs. If statement handles youtube, twitter, flickr; else statement handles iNat results
        if self.dbName == 'youtube' or self.dbName == 'twitter' or self.dbName == 'flickr_june_2019':
            res = self.db[collection].find({"$and": [{"wild": True},{keys[self.dbName]:{"$gte": self.timeFrameStart}}]})
        else:
            res = self.db[collection].find({"$and": [{'captive': False},{'time_observed_utc': {"$gte":self.timeFrameStart}}]})
        
        ## create a list of all the times (in original UTC format) our res docs were created at
        self.timePosts = [x[keys[self.dbName]] for x in res]
        if len(self.timePosts) < 1:
            print("No videos were processed yet.")
            return
        
        ## self.dates() is a list of datetime.date() objects of wild encounters within the time frame
        #it converts .datetime objs to more general .date objs (easier to work with)
        #and then sorts the converted dates in a list with most recent at beginning and least recent towards end
        self.dates = [x.date() for x in self.timePosts] 
        self.dates.sort() 

        # Find the difference in days between posting dates of successive posts
        lastDate = [self.dates[0]]  #stores all the dates we have already looked at
        timeDiffs = []
        for date in self.dates:
            res = abs(date - lastDate[-1]) #find the time difference between current and previous, most recent post
            timeDiffs.append(res.days)
            lastDate.append(date)

        #plot the time delays using seaborn histogram
        plt.figure(figsize=(20,20))
        sns.histplot(data=timeDiffs, bins=10)
        plt.xlabel('Days between succesive posts')
        plt.ylabel('Number of posts')
        plt.title('Histogram for Time Between Succesive Wild Posts')

        return self.dates
    
    
    ## function to plot posts per week, with and without a simple moving avg filter
    ## postsPerWeekDict contains values without moving avg filter
    ## smas contains values with moving avg filter
    def plotPostsPerWeek(self, postsPerWeekDict, smas, collection):
        ## keys correspond to week # (x-axis)
        ## values correspond to number of posts per week (y-axis)
        ppw_keys = list(postsPerWeekDict.keys())
        ppw_values =  list(postsPerWeekDict.values())
        
        ## pad simple moving avgs with two 0s at beginning 
        smas = insert(smas, 0,0) 
        smas = insert(smas, 0,0)
        
        #plot posts per week and average posts per week
        fig, plt_ppw = plt.subplots(1,1,figsize=(10,10))    
        plt_ppw.plot(ppw_keys, ppw_values, label="no moving avg filter")
        plt_ppw.plot(ppw_keys, smas, label="moving avg filter applied")
        plt_ppw.set_title("Posts Per Week for wild encounters in {} collection".format(collection))
        plt_ppw.set(xlabel = "Week", ylabel = "Number of Posts")
        plt_ppw.legend(loc="lower left")
        
        
    def queryTermPieCharts(self, df, species_name):
        #drop the last row (totals)
        #df.drop(df.tail(1).index,inplace=True)
        
        
        fig, ax = plt.subplots(figsize = (10,10))
        size = 0.3
        
        #populate vals[] - the 2d array we use to make our pie charts
        #col1 = wild count, col2 = captive count, rows are each different collection
        vals = np.zeros((len(df), 2)) 
        for index, row in df.iterrows():
            vals[index] = np.array((row["Wild_Count"],row["Captive_Count"]))

        
        #sorting out the colors
        cmap = plt.get_cmap("tab20c")
        outer_colors = cmap(np.arange(3)*4)
        inner_colors = cmap([1, 2, 5, 6, 9, 10])
        
        #outer pie chart - consists of the entire collection relevant percentage
        ax.pie(df['Relevant_Count'].tolist(), radius=1, colors=outer_colors, labels = df['Col_Name'],
               wedgeprops=dict(width=size, edgecolor='w'), \
               pctdistance=0.8, \
               startangle=90, \
               textprops={'color':"k", 'fontsize': 18} )

        #create wild, captive labels for inner pie chart components
        inner_labels = [['wild', 'captive'] for col in df['Col_Name']] #['wild', 'captive','wild', 'captive', ...]
        inner_labels_flat = [item for sublist in inner_labels for item in sublist]
        
        print(inner_labels_flat)
        print(vals.flatten())
        
        #inner pie chart components - split up into %wild and %CAPTIVE for each collection
        ax.pie(vals.flatten(), radius=1-size, colors=inner_colors, labels = inner_labels_flat, labeldistance = 1.05, \
               wedgeprops=dict(width=size, edgecolor='w'), \
               autopct='%1.1f%%', pctdistance=0.8, startangle=90, \
               textprops={'color':"w", 'fontsize': 14})

        ax.set(aspect="equal", title='Pie plot with `ax.pie`')
        plt.title(species_name)
        plt.show()
        
        
    def queryTermPieChartsV2(self, data):
        #https://towardsdatascience.com/donut-plot-with-matplotlib-python-be3451f22704
        
        #create donut plots
        startingRadius = 0.7 + (0.3* (len(data)-1))
        
        for index, row in data.iterrows():
            wild = row["Wild_Count"]
            captive = row["Captive_Count"]
            relevant = row["Relevant_Count"]
            
            textLabel = 'Relevant: ' + str(relevant) #row['Col_Name'] + ' relevant' #'captive: ' + str(captive) + 'wild: ' + str(wild) 
                        
            donut_sizes = [wild, captive]
            
            plt.text(0.01, startingRadius + 0.07, textLabel, horizontalalignment='center', verticalalignment='center')
            plt.pie(donut_sizes, radius=startingRadius, startangle=90, colors=['#d5f6da', '#5cdb6f'],
                    wedgeprops={"edgecolor": "white", 'linewidth': 1})

            startingRadius-=0.3

        # equal ensures pie chart is drawn as a circle (equal aspect ratio)
        plt.axis('equal')

        # create circle and place onto pie chart
        circle = plt.Circle(xy=(0, 0), radius=0.35, facecolor='white')
        plt.gca().add_artist(circle)
        plt.savefig('donutPlot.jpg')
        plt.show()
  
    
    #get outer colors for outer pie chart and gradients for inner pie chart colors
    def get_inner_outer_colors(self, len_df):
        cmap = plt.get_cmap("tab20c")
        outer_ind = np.arange(len_df) * 4
        inner_ind = []
        for ind in outer_ind:
            inner_ind.append(ind + 1)
            inner_ind.append(ind + 2)
        
        outer_colors = cmap(outer_ind)
        inner_colors = cmap(inner_ind)
        
        return outer_colors, inner_colors
      
    
    #legend and unique colors for each collection
    def queryTermPieChartsV3(self, df):
        
        fig, ax = plt.subplots(figsize = (10,10))
        size = 0.3
        
        #populate vals[] - the 2d array we use to make our pie charts
        #col1 = wild count, col2 = captive count, rows are each different collection
        vals = np.zeros((len(df), 2)) 
        for index, row in df.iterrows():
            vals[index] = np.array((row["Wild_Count"],row["Captive_Count"]))

        #sorting out the colors
        outer_colors, inner_colors = self.get_inner_outer_colors(len(df))
        
        #outer pie chart - consists of the entire collection relevant percentage
        ax.pie(df['Relevant_Count'].tolist(), radius=1, colors=outer_colors,
                           wedgeprops=dict(width=size, edgecolor='w'), \
                           pctdistance=0.8, \
                           startangle=90, \
                           textprops={'color':"k", 'fontsize': 10} )

        #create wild, captive labels for inner pie chart components
        inner_labels = [['wild', 'captive'] for col in df['Col_Name']] #['wild', 'captive','wild', 'captive', ...]
        inner_labels_flat = [item for sublist in inner_labels for item in sublist]
        
        #inner pie chart components - split up into %wild and %CAPTIVE for each collection
        ax.pie(vals.flatten(), radius=1-size, colors=inner_colors, \
               wedgeprops=dict(width=size, edgecolor='w'), \
               autopct='%1.1f%%', pctdistance=0.8, startangle=90, \
               textprops={'color':"w", 'fontsize': 0})

        #combined labels
        tot_rel = df['Relevant_Count'].sum()
        vals_percent = vals/tot_rel * 100
        vals_rounded = [np.round(percent, 1) for percent in vals_percent]
        combined_labels = [df['Col_Name'][i] + ' '+ str(vals_rounded[i]) for i in range(0, len(df))]
        raw_combined_labels = [df['Col_Name'][i] + ' '+ str(vals[i]) for i in range(0, len(df))]
        
        #outer pie chart legend with names of each collection and its corresponding color #df['Col_Name']
        legend1= plt.legend( combined_labels, loc= "upper left", bbox_to_anchor = (1,1), title = "Query Term Collections [%Wild, %Captive]")
        
        #inner pie chart legend with percentage breakdown of each collection [wild]
        legend2= plt.legend(raw_combined_labels, loc= "lower left", bbox_to_anchor = (1,0.1), title = \
                            "Query Term Collections [Num Wild, Num Captive]")
        
        #include both legends with pie chart
        ax.add_artist(legend1)
        ax.add_artist(legend2)
    
        plt.show()