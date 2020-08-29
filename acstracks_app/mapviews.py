from django.conf import settings
import os
import gpxpy
import gpxpy.gpx
import folium


def process_gpx_file(filename):
    fullfilename = os.path.join(
        settings.MEDIA_ROOT,
        filename
    )

    gpx_file = open(fullfilename, 'r')

    gpx = gpxpy.parse(gpx_file)
    points = []
    for track in gpx.tracks:
        for segment in track.segments:        
            for point in segment.points:
                points.append(tuple([point.latitude, point.longitude]))
    # print(points)
    ave_lat = sum(p[0] for p in points)/len(points)
    ave_lon = sum(p[1] for p in points)/len(points)

    # Load map centred on average coordinates
    my_map = folium.Map(location=[ave_lat, ave_lon], zoom_start=12)

    min_lat = float(9999999)
    max_lat = float(-9999999)
    min_lon = float(9999999)
    max_lon = float(-9999999)
    for p in points:
        if min_lat > p[0]:
            min_lat = p[0]
        if max_lat < p[0]:
            max_lat = p[0]
        if min_lon > p[1]:
            min_lon = p[1]
        if max_lon < p[1]:
            max_lon = p[1]

    sw = tuple([min_lat, min_lon])
    ne = tuple([max_lat, max_lon])

    my_map.fit_bounds([sw, ne]) 


    # add a markers
    # for each in points:  
    #     folium.Marker(each).add_to(my_map)
    # folium.Marker(points[0], icon=folium.Icon(color='lightgray', icon='home', prefix='fa')).add_to(my_map)

    # nice green circle
    folium.vector_layers.CircleMarker(
            location=[points[0][0], points[0][1]],
            radius=12,
            color="white",
            weight=1,
            fill_color="green",
            fill_opacity=1
        ).add_to(my_map) 

    # OVERLAY triangle
    folium.RegularPolygonMarker(
            location=[points[0][0], points[0][1]],
            fill_color="white",
            fill_opacity=1,
            color="white",
            number_of_sides=3,
            radius=4,
            rotation=0,
        ).add_to(my_map)

    # nice red circle
    folium.vector_layers.CircleMarker(
            location=[points[-1][0], points[-1][1]],
            radius=12,
            color="white",
            weight=1,
            fill_color="red",
            fill_opacity=1
        ).add_to(my_map) 

     # OVERLAY square
    folium.RegularPolygonMarker(
            location=[points[-1][0], points[-1][1]],
            fill_color="white",
            fill_opacity=1,
            color="white",
            number_of_sides=4,
            radius=4,
            rotation=45,
            popup="popup"
        ).add_to(my_map)
 
    # folium.LayerControl(collapsed=True).add_to(my_map)

    # add lines
    folium.PolyLine(points, color="red", weight=2.5, opacity=1).add_to(my_map)

    # Save map
    mapfilename = os.path.join(
            settings.MAPS_ROOT,
            "map.html"
        )
    my_map.save(mapfilename)
 
    return
