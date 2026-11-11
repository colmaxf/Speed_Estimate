class TrackableObject:
	def __init__(self, objectID, centroid,timeAvg = 0, time_avg2 =0):
		# store the object ID, then initialize a list of centroids
		# using the current centroid
		self.objectID = objectID
		self.centroids = [centroid]
		self.time_cal = [timeAvg]
		self.time_test1 = timeAvg
		self.time_test2 = time_avg2
		# initialize a boolean used to indicate if the object has
		# already been counted or not
		self.counted = False