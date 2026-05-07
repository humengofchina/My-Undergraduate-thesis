import folium
import requests
import time
import math
# 此文件用于绘制真实路网环境的配送线路
# ==========================================
# 1. 数据准备 (请确保 routes 填入的是最新的 6 辆车的结果)
# ==========================================
locations = {
    0:(113.5765967,34.8941855), 1:(113.5561377,34.7409250), 2:(113.6140946,34.7551608),
    3:(113.5512827,34.8198692), 4:(113.6623274,34.7548116), 5:(113.6497080,34.8608752),
    6:(113.8006427,34.7924848), 7:(113.8981885,34.7805231), 8:(113.6867657,34.6205619),
    9:(113.7047691,34.6058205), 10:(113.6715036,34.6890026), 11:(113.6931873,34.7242179),
    12:(113.7462298,34.7429335), 13:(113.6639847,34.8033946), 14:(113.6662585,34.7836224),
    15:(113.6052876,34.8607039), 16:(113.7593603,34.7686597), 17:(113.7130126,34.7713199),
    18:(113.6750943,34.7864745), 19:(113.6572006,34.8075965), 20:(113.6514886,34.8073216),
    21:(113.6210658,34.7409270), 22:(113.6931797,34.7545588), 23:(113.6242167,34.8310125),
    24:(113.6378998,34.8612780), 25:(113.5346314,34.8154432), 26:(113.7289247,34.7642198),
    27:(113.7290246,34.7487973),
}

# main文件求解出的配送任务
routes = [[0, 15, 23, 20, 19, 13, 14, 18, 0], [0, 27, 12, 16, 26, 17, 0], [0, 8, 9, 10, 0], [0, 2, 21, 4, 11, 22, 0], [0, 3, 1, 25, 0], [0, 24, 5, 6, 7, 0]]

# 车辆线路颜色
colors = ['blue', 'orange', 'green', 'red', 'purple', 'darkred']

# ==========================================
# 2. 初始化交互式地图
# ==========================================
center_lat = 34.76
center_lon = 113.65
m = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles='CartoDB positron')

for node_id, (lon, lat) in locations.items():
    if node_id == 0:
        folium.Marker([lat, lon], popup="配送中心", icon=folium.Icon(color='red', icon='home')).add_to(m)
    else:
        folium.CircleMarker(
            location=[lat, lon], radius=6, popup=f"客户 {node_id}",
            color='black', fill=True, fill_color='white'
        ).add_to(m)

# ==========================================
# 3. 核心 API 请求与里程提取
# ==========================================
def get_real_route_and_distance(lon1, lat1, lon2, lat2):
    """
    调用 OSRM 接口获取真实路网轨迹以及路段物理距离
    返回: (路网经纬度序列, 真实距离_单位米)
    """
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    try:
        response = requests.get(url)
        data = response.json()
        if data['code'] == 'Ok':
            coordinates = data['routes'][0]['geometry']['coordinates']
            distance_meters = data['routes'][0]['distance'] # 提取接口返回的真实路段距离
            
            route_shape = [[lat, lon] for lon, lat in coordinates]
            return route_shape, distance_meters
    except Exception as e:
        pass
    
    # 如果 API 请求失败，作为备用方案计算直线的球面距离
    print(f"⚠️ 警告: 节点获取路网失败，已降级为直线距离")
    R = 6371000 # 地球半径(米)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    fallback_distance = 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return [[lat1, lon1], [lat2, lon2]], fallback_distance

# ==========================================
# 4. 绘制路线并统计总里程
# ==========================================
print("正在向服务器请求真实路网数据及里程，请稍候...\n")

total_fleet_distance_km = 0 # 整个车队总里程

for vehicle_id, route in enumerate(routes):
    color = colors[vehicle_id % len(colors)]
    vehicle_distance_meters = 0 # 单辆车里程
    
    for i in range(len(route) - 1):
        start_node = route[i]
        end_node = route[i + 1]
        
        lon1, lat1 = locations[start_node]
        lon2, lat2 = locations[end_node]
        
        # 获取路线形状和真实距离
        route_shape, segment_distance = get_real_route_and_distance(lon1, lat1, lon2, lat2)
        vehicle_distance_meters += segment_distance
        
        segment_km = segment_distance / 1000.0
        
        # 在地图上划线，并在 tooltip 中加入距离信息
        folium.PolyLine(
            locations=route_shape,
            color=color,
            weight=5,
            opacity=0.8,
            tooltip=f"车辆 {vehicle_id + 1} ({start_node} -> {end_node}) | 真实路程: {segment_km:.2f} km"
        ).add_to(m)
        
        time.sleep(0.2) # 防止被 API 限流
        
    vehicle_km = vehicle_distance_meters / 1000.0
    total_fleet_distance_km += vehicle_km
    print(f"🚚 冷藏车 {vehicle_id + 1} 真实行驶里程: {vehicle_km:>6.2f} km")

print("-" * 40)
print(f"🏁 6 辆车真实路网总行驶里程: {total_fleet_distance_km:.2f} km")

# ==========================================
# 5. 保存输出
# ==========================================
output_file = "zhengzhou_real_routing.html"
m.save(output_file)
print(f"\n✅ 渲染完成！已保存为 '{output_file}'。")