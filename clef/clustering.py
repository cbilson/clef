import numpy as np
import scipy
import heapq
import random
from sklearn import datasets #for testing only

import clef.spotify

def kmeans(data, n_clusters):
    #find minimum and maximum dimensions
    min_dims = []
    max_dims = []
    s = data.shape
    for i in range(s[len(s)-1]):
        min_dims.append(np.ndarray.min(data[:,i]))
        max_dims.append(np.ndarray.max(data[:,i]))

    # build initial random centroids
    centroids = []
    for i in range(n_clusters):
        c = []
        for j in range(len(min_dims)):
            c.append(random.uniform(min_dims[j], max_dims[j]))
        centroids.append(np.array(c))
    centroids = np.array(centroids)

    # clustering begins
    old_centroids = []
    for i in range(centroids.size):
        old_centroids.append(np.zeros(centroids[0].size))
    old_centroids = np.array(old_centroids)

    assigned = []
    #while centroids are still changing
    while not np.array_equal(old_centroids, centroids):
        clusters = []
        # assign data points to closest centroid
        for n in range(data.shape[0]):
            dists = []
            for c in range(centroids.shape[0]):
                dists.append(scipy.spatial.distance.euclidean(data[n],centroids[c]))
            assigned.append(dists.index(min(dists)))

        # recalculate centroids
        old_centroids = centroids
        for i in range(n_clusters):
            cluster = []
            for n in range(len(assigned)):
                if assigned[n] == i:
                    cluster.append(data[n])
            cluster = np.array(cluster)
            if cluster.size != 0:
                centroids[i] = np.sum(cluster) / cluster.size
            clusters.append(cluster)
    return centroids, clusters

# TEST OF KMEANS()
'''d = datasets.load_iris().data
centroids, clusters = kmeans(d, 3)
print(centroids)
print(clusters)'''

def recommend(track_id, average_vector):
    spotify_recs = get_data(song)
    centroids, clusters = kmeans(spotify_recs, 3)
    min_dist = FLOAT.MAXIMUM
    minn = 3
    for c in range(centroids.shape[0]):
        if scipy.spatial.distance.euclidean(centroid[c], average_vector) < min_dist:
            min_dist = scipy.spatial.distance.euclidean(centroid[c], average_vector)
            minn = c
    return clusters[minn]
