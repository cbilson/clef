import numpy as np
import scipy
import random
import clef.spotify as spotify

from sklearn import datasets #for testing only

from clef import app

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

def recommend(user, seed_tracks, user_avg):
    spotify_recs = spotify.get_recommendations(user, seed_tracks)
    if spotify_recs is None: return None
    spotify_recs = list(spotify_recs)
    for r in spotify_recs:
        app.logger.debug("Spotify Recommends: %s, from %s, by %s (id:%s)"
                         % (r['name'], r['album']['name'], ';'.join([a['name'] for a in r['artists']]), r['id']))

    spotify_rec_features = spotify.get_audio_features(user, [r['id'] for r in spotify_recs])
    if spotify_rec_features is None: return None
    spotify_rec_features = list(spotify_rec_features)

    # exclude tracks for which we weren't able to get attributes
    app.logger.debug("Number of tracks before culling nulls: %s" % len(spotify_rec_features))
    valid_features = list([a for a in spotify_rec_features
                           if a['acousticness'] is not None
                           and a['danceability'] is not None
                           and a['energy'] is not None
                           and a['instrumentalness'] is not None
                           and a['liveness'] is not None
                           and a['loudness'] is not None
                           and a['speechiness'] is not None
                           and a['valence'] is not None
                           and a['tempo'] is not None])
    app.logger.debug("Number of tracks after culling nulls: %s" % len(valid_features))

    track_ids = [a['id'] for a in valid_features]
    keys = ['acousticness', 'danceability', 'energy', 'instrumentalness', 'liveness', 'loudness',
            'speechiness', 'valence', 'tempo']
    data = np.array([[a[k] for k in keys] for a in valid_features], np.float32)
    centroids, clusters = kmeans(data, 3)
    min_dist = np.finfo(np.float32).max
    minn = 3

    # 1st and 2nd columns are user_id and # tracks used to compute averages
    a = np.array([user_avg[i+2] for i in range(len(keys))], np.float32)
    for c in range(centroids.shape[0]):
        d = scipy.spatial.distance.euclidean(centroids[c], a)
        if d < min_dist:
            min_dist = d
            minn = c

    app.logger.debug("Min Dist: %s" % min_dist)
    app.logger.debug("Track ID: %s" % track_ids[minn])

    return next(spotify.get_tracks(user, [track_ids[minn]]))
