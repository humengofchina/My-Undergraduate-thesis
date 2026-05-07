import folium
import requests
import time

# ==========================================
# 1. 数据准备
# ==========================================
# 你的经纬度字典
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

# 注意：请将这里替换为你刚才用 OR-Tools 跑出来的实际 routes 数组！
# 
# routes = [[0, 10, 8, 9, 0], [0, 7, 6, 16, 0], [0, 19, 13, 17, 26, 12, 27, 0], 
#           [0, 20, 14, 4, 11, 22, 18, 0], [0, 3, 25, 1, 21, 2, 0], [0, 15, 23, 5, 24, 0]]
routes = [[0, 15, 23, 20, 19, 13, 14, 18, 0], [0, 27, 12, 16, 26, 17, 0], [0, 8, 9, 10, 0],
           [0, 2, 21, 4, 11, 22, 0], [0, 3, 1, 25, 0], [0, 24, 5, 6, 7, 0]]
# routes = [
#     [0, 25, 3, 15, 24, 5, 0],
#     [0, 23, 20, 19, 13, 14, 18, 0],
#     [0, 4, 22, 12, 27, 26, 0],
#     [0, 17, 16, 6, 7, 0],
#     [0, 2, 21, 1, 0],
#     [0, 11, 10, 9, 8, 0]
# ]

colors = ['blue', 'orange', 'green', 'red', 'purple', 'darkred']

# ==========================================
# 2. 初始化交互式地图
# ==========================================
# 以郑州市中心为原点初始化地图，设定初始缩放级别
center_lat = 34.76
center_lon = 113.65
m = folium.Map(location=[center_lat, center_lon], zoom_start=11, tiles='CartoDB positron')

# 添加节点标记
for node_id, (lon, lat) in locations.items():
    if node_id == 0:
        folium.Marker(
            [lat, lon], 
            popup="配送中心", 
            icon=folium.Icon(color='red', icon='home')
        ).add_to(m)
    else:
        # 客户点：用圆圈表示
        folium.CircleMarker(
            location=[lat, lon],
            radius=6,
            popup=f"客户 {node_id}",
            color='black',
            fill=True,
            fill_color='white'
        ).add_to(m)

# ==========================================
# 3. 通过 OSRM API 获取真实路网轨迹
# ==========================================
def get_real_route(lon1, lat1, lon2, lat2):
    """调用 OSRM 开源路由 API 获取两点之间的真实道路经纬度序列"""
    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson"
    try:
        response = requests.get(url)
        data = response.json()
        if data['code'] == 'Ok':
            # 提取沿途的经纬度坐标列表
            coordinates = data['routes'][0]['geometry']['coordinates']
            # OSRM 返回的是 [lon, lat]，Folium 划线需要的是 [lat, lon]，因此需要对调
            return [[lat, lon] for lon, lat in coordinates]
    except Exception as e:
        print(f"获取路网失败: {e}")
    return [[lat1, lon1], [lat2, lon2]] # 如果失败，降级为画直线

print("正在向服务器请求真实路网数据，请稍候...")

for vehicle_id, route in enumerate(routes):
    color = colors[vehicle_id % len(colors)]
    
    # 将一辆车的所有途经点组合在一起
    for i in range(len(route) - 1):
        start_node = route[i]
        end_node = route[i + 1]
        
        lon1, lat1 = locations[start_node]
        lon2, lat2 = locations[end_node]
        
        # 获取真实路线形状点
        route_shape = get_real_route(lon1, lat1, lon2, lat2)
        
        # 在地图上绘制沿路的线
        folium.PolyLine(
            locations=route_shape,
            color=color,
            weight=5,
            opacity=0.8,
            tooltip=f"车辆 {vehicle_id + 1} ({start_node} -> {end_node})"
        ).add_to(m)
        
        # 增加极短的延时，防止触发 OSRM 免费接口的频率限制被拉黑
        time.sleep(0.2)

# ==========================================
# 4. 保存为网页文件
# ==========================================
output_file = "zhengzhou_real_routing.html"
m.save(output_file)
print(f"\n✅ 渲染完成！请在你的文件夹中找到并双击打开 '{output_file}' 查看真实道路地图。")