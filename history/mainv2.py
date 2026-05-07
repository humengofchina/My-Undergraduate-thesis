import math
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# ==========================================
# 1. 数据录入区
# ==========================================
def create_data_model():
    """存储所有输入数据"""
    data = {}
    
    # 客户坐标位置_Python字典形式 (格式: 经度, 纬度)
    data['locations'] = {
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
    
    data['num_vehicles'] = 6
    data['depot'] = 0
    
    # 客户需求量_Python字典形式 (单位：千克)
    demand_sum = {
        0:0, 1:64, 2:72, 3:62, 4:66, 5:68, 6:64, 7:73, 8:73, 9:66, 10:70, 
        11:67, 12:68, 13:71, 14:65, 15:66, 16:67, 17:64, 18:63, 19:68, 20:69, 
        21:69, 22:62, 23:65, 24:72, 25:71, 26:70, 27:72
    }
    # 将字典转换为 OR-Tools 需要的列表格式 (按索引 0-27 排序)
    data['demands'] = [demand_sum[i] for i in range(28)]
    
    # 【注意】：由于总需求是 1827 kg，6辆车平均每辆需装载约 305 kg。
    # 这里将额定载重设为 400 kg。
    data['vehicle_capacities'] = [400] * 6
    
    # 统一时间窗口 0-120分钟 (即 5:00 - 7:00)
    data['time_windows'] = [(0, 120)] * 28
    
    # 市区车速假设 50 km/h
    data['vehicle_speed_km_per_min'] = 50 / 60.0
    # 每个客户固定卸货服务时间 (分钟)
    data['service_time_per_customer'] = 10 
    
    return data

# ==========================================
# 2. 距离矩阵计算
# ==========================================
def calculate_haversine_distance(coord1, coord2):
    """计算两点间的实际球面距离 (单位: km)"""
    lon1, lat1 = coord1 
    lon2, lat2 = coord2
    R = 6371  
    
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def build_matrices(data):
    num_locations = len(data['locations'])
    time_matrix = [[0] * num_locations for _ in range(num_locations)]
    
    for i in range(num_locations):
        for j in range(num_locations):
            if i != j:
                dist = calculate_haversine_distance(data['locations'][i], data['locations'][j])
                travel_time = dist / data['vehicle_speed_km_per_min']
                service_time = data['service_time_per_customer'] if j != data['depot'] else 0
                time_matrix[i][j] = math.ceil(travel_time + service_time)
                
    return time_matrix

# ==========================================
# 3. 求解与输出
# ==========================================
def print_solution(data, manager, routing, solution):
    print(f'=== 大河四季冷链配送优化方案 ===\n')
    time_dimension = routing.GetDimensionOrDie('Time')
    total_time = 0
    total_load = 0
    
    # 用于收集画图需要的路线数组
    routes_for_plot = []
    
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        plan_output = f'冷藏车 {vehicle_id + 1} 路线:\n'
        route_load = 0
        route = [] # 记录当前车辆的节点顺序
        
        while not routing.IsEnd(index):
            time_var = time_dimension.CumulVar(index)
            node_index = manager.IndexToNode(index)
            route.append(node_index)
            route_load += data['demands'][node_index]
            
            arrival_minute = solution.Min(time_var)
            hour = 5 + arrival_minute // 60
            minute = arrival_minute % 60
            
            plan_output += f' 节点 {node_index:>2} (到达: {hour:02d}:{minute:02d}, 累计载重: {route_load}kg) -> '
            index = solution.Value(routing.NextVar(index))
            
        time_var = time_dimension.CumulVar(index)
        arrival_minute = solution.Min(time_var)
        hour = 5 + arrival_minute // 60
        minute = arrival_minute % 60
        
        route.append(data['depot']) # 添加返回终点
        routes_for_plot.append(route)
        
        plan_output += f'返回中心 (到达: {hour:02d}:{minute:02d})\n'
        plan_output += f'行驶与服务耗时: {solution.Min(time_var)} 分钟\n'
        print(plan_output)
        
        total_time += solution.Min(time_var)
        total_load += route_load
        
    print("-" * 50)
    print(f'总耗时 (优化目标): {total_time} 分钟')
    print(f'总配送重量: {total_load} kg')
    print(f'\n请将以下数组复制到img.py画图代码中替换原有的 routes 变量：')
    print(f'routes = {routes_for_plot}')

def main():
    data = create_data_model()
    time_matrix = build_matrices(data)
    
    manager = pywrapcp.RoutingIndexManager(len(data['time_windows']), data['num_vehicles'], data['depot'])
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return time_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(demand_callback_index, 0, data['vehicle_capacities'], True, 'Capacity')

    routing.AddDimension(transit_callback_index, 30, 120, False, 'Time')
    time_dimension = routing.GetDimensionOrDie('Time')

    for location_idx, time_window in enumerate(data['time_windows']):
        if location_idx == data['depot']:
            continue
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

    depot_idx = data['depot']
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        time_dimension.CumulVar(index).SetRange(data['time_windows'][depot_idx][0], data['time_windows'][depot_idx][1])
        end_index = routing.End(vehicle_id)
        time_dimension.CumulVar(end_index).SetRange(data['time_windows'][depot_idx][0], data['time_windows'][depot_idx][1])

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    search_parameters.time_limit.seconds = 15 

    solution = routing.SolveWithParameters(search_parameters)
    if solution:
        print_solution(data, manager, routing, solution)
    else:
        print("求解失败：车辆无法在规定约束内完成任务。可能是 2 小时时间太短，或者载重超限。")

if __name__ == '__main__':
    main()