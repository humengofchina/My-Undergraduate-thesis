import math
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# 此为为论文反复推敲后的第四版文件，用于求解配送车辆数量及每辆车的配送任务

# ==========================================
# 1. 数据录入区
# ==========================================
def create_data_model():
    """存储所有输入数据"""
    data = {}
    
    # 1. 客户点经纬度坐标
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
    
    # 2. 车辆最大数量和车辆额定载重输入
    data['num_vehicles'] = 10 
    data['depot'] = 0
    data['vehicle_capacities'] = [800] * data['num_vehicles'] 
    
    # 3. 客户点货物需求量 (千克)
    demand_sum = {
        0:0, 1:64, 2:72, 3:62, 4:66, 5:68, 6:64, 7:73, 8:73, 9:66, 10:70, 
        11:67, 12:68, 13:71, 14:65, 15:66, 16:67, 17:64, 18:63, 19:68, 20:69, 
        21:69, 22:62, 23:65, 24:72, 25:71, 26:70, 27:72
    }
    data['demands'] = [demand_sum[i] for i in range(28)]
    
    # 4. 客户点独立时间要求 (分钟)
    time_windows_dict = {
        0:(0,120), 1:(30,60), 2:(30,60), 3:(20,50), 4:(40,70), 5:(20,40),
        6:(50,110), 7:(50,110), 8:(50,90), 9:(50,110), 10:(30,100), 11:(20,90),
        12:(40,110), 13:(20,100), 14:(30,90), 15:(10,50), 16:(30,100), 17:(30,100),
        18:(20,100), 19:(20,90), 20:(10,60), 21:(30,90), 22:(30,100), 23:(10,50),
        24:(10,60), 25:(20,70), 26:(30,100), 27:(20,90),
    }
    data['time_windows'] = [time_windows_dict[i] for i in range(28)]
    
    # 5. 核心业务参数
    # 设定为临界车速: 50 km/h (即 50/60 km/min)
    data['vehicle_speed_km_per_min'] = 50 / 60.0  
    data['service_time_per_customer'] = 10        # 每站卸货 10 分钟
    
    return data

# ==========================================
# 2. 地理距离与时间矩阵计算
# ==========================================
def calculate_haversine_distance(coord1, coord2):
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
# 3. 求解与格式化输出
# ==========================================
def print_solution(data, manager, routing, solution):
    print(f'\n{"="*50}')
    print(f'=== 大河四季冷链物流有限公司2026新增客户配送线路优化结果===')
    print(f'{"="*50}\n')
    
    time_dimension = routing.GetDimensionOrDie('Time')
    total_time = 0
    total_load = 0
    active_vehicles = 0
    routes_for_plot = []
    
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        
        # 跳过未被分配任务的空闲车辆
        if routing.IsEnd(solution.Value(routing.NextVar(index))):
            continue
            
        active_vehicles += 1
        plan_output = f'📌 实际出车 {active_vehicles} 的配送路线:\n'
        route_load = 0
        route = [] 
        
        while not routing.IsEnd(index):
            time_var = time_dimension.CumulVar(index)
            node_index = manager.IndexToNode(index)
            route.append(node_index)
            route_load += data['demands'][node_index]
            
            arrival_minute = solution.Min(time_var)
            hour = 5 + arrival_minute // 60
            minute = arrival_minute % 60
            
            # 提取客户要求的时间要求以供对比
            tw_start, tw_end = data['time_windows'][node_index]
            tw_str = f"[{tw_start}-{tw_end}分]" if node_index != 0 else ""
            
            plan_output += f'   节点 {node_index:>2} {tw_str:<10} (抵达: {hour:02d}:{minute:02d}, 当前载重: {route_load:>3}kg) ->\n'
            index = solution.Value(routing.NextVar(index))
            
        time_var = time_dimension.CumulVar(index)
        arrival_minute = solution.Min(time_var)
        hour = 5 + arrival_minute // 60
        minute = arrival_minute % 60
        
        route.append(data['depot']) 
        routes_for_plot.append(route)
        
        plan_output += f'   返回配送中心       (抵达: {hour:02d}:{minute:02d})\n'
        plan_output += f'   >> 该车行驶与等待总耗时: {solution.Min(time_var)} 分钟\n'
        print(plan_output)
        
        total_time += solution.Min(time_var)
        total_load += route_load
        
    print("-" * 50)
    print(f'优化完成：')
    print(f'启用最少车辆数: {active_vehicles} 辆 (备选池: {data["num_vehicles"]}辆)')
    print(f'所有车辆总耗时 (时间成本): {total_time} 分钟')
    print(f'所有车辆总配送重量: {total_load} kg')
    print(f'\n用于 Matplotlib / Folium 画图的路线数组：')
    print(f'routes = {routes_for_plot}\n')

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

    # 最小化车辆数
    # 给每一辆车赋予高昂的固定启动成本，迫使算法在满足条件的情况下尽量少派车
    routing.SetFixedCostOfAllVehicles(100000)

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(demand_callback_index, 0, data['vehicle_capacities'], True, 'Capacity')

    routing.AddDimension(transit_callback_index, 120, 120, False, 'Time')
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
    
    search_parameters.time_limit.seconds = 30 

    print("模型启动中：正在执行优化")
    print("求解器正在进行，请耐心等待...\n")
    
    solution = routing.SolveWithParameters(search_parameters)
    
    if solution:
        print_solution(data, manager, routing, solution)
    else:
        print("\n 求解失败：当前约束条件无法找到可行解！")

if __name__ == '__main__':
    main()