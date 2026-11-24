class DLSNode:
    def __init__(self, node_id, parent_id, state, action, depth, status="GENERATED"):
        self.node_id = node_id
        self.parent_id = parent_id
        self.state = state
        self.action = action
        self.depth = depth
        self.status = status

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "parent_id": self.parent_id,
            "state": self.state,
            "action": self.action,
            "depth": self.depth,
            "status": self.status
        }

def run_dls(start_state, target_state, depth_limit, capacity):
    """
    Executes a real branching Depth-Limited Search over water tank states.
    Valid actions: FILL_100 (+100), FILL_200 (+200), DRAIN_100 (-100), DRAIN_200 (-200).
    """
    # Validate target boundaries
    if target_state < 0 or target_state > capacity or target_state % 100 != 0:
        return {
            "target_found": False,
            "initial_state": start_state,
            "target_state": target_state,
            "path": [],
            "visited_states": [],
            "traversal_order": [],
            "explored_nodes": 0,
            "generated_nodes": 0,
            "pruned_nodes": 0,
            "depth_limit": depth_limit,
            "target_depth": 0,
            "termination_reason": "INVALID_TARGET",
            "nodes": []
        }

    # Validate start boundaries
    if start_state < 0 or start_state > capacity or start_state % 100 != 0:
        return {
            "target_found": False,
            "initial_state": start_state,
            "target_state": target_state,
            "path": [],
            "visited_states": [],
            "traversal_order": [],
            "explored_nodes": 0,
            "generated_nodes": 0,
            "pruned_nodes": 0,
            "depth_limit": depth_limit,
            "target_depth": 0,
            "termination_reason": "STATE_SPACE_EXHAUSTED",
            "nodes": []
        }

    all_nodes = {}
    node_id_counter = [0]
    explored_nodes_count = [0]
    generated_nodes_count = [0]
    pruned_nodes_count = [0]
    traversal_order = []
    
    # Create the root node
    root_node = DLSNode(
        node_id=0,
        parent_id=None,
        state=start_state,
        action="START",
        depth=0,
        status="VISITED"
    )
    all_nodes[0] = root_node
    generated_nodes_count[0] += 1
    
    # Debug validations (Step 10)
    assert root_node.depth == 0, "Root depth must be 0"
    assert root_node.state == start_state, "Root state must match initial_state"
    
    active_path_states = {start_state}
    
    # Target node holder to reconstruct path
    target_node = None
    if start_state == target_state:
        root_node.status = "TARGET"
        target_node = root_node
    
    def dls_visit(node):
        nonlocal target_node
        traversal_order.append(node.state)
        explored_nodes_count[0] += 1
        
        # Base Case 1: Target reached
        if node.state == target_state:
            node.status = "TARGET"
            target_node = node
            return [node]
            
        # Base Case 2: Depth limit reached (cannot expand children)
        if node.depth >= depth_limit:
            return None
            
        # Branch actions: FILL_100, FILL_200, DRAIN_100, DRAIN_200
        actions = [
            ("FILL_100", 100),
            ("FILL_200", 200),
            ("DRAIN_100", -100),
            ("DRAIN_200", -200)
        ]
        
        for action_name, change in actions:
            next_state = node.state + change
            node_id_counter[0] += 1
            child_id = node_id_counter[0]
            
            child = DLSNode(
                node_id=child_id,
                parent_id=node.node_id,
                state=next_state,
                action=action_name,
                depth=node.depth + 1,
                status="GENERATED"
            )
            all_nodes[child_id] = child
            generated_nodes_count[0] += 1
            
            # Debug validation (Step 10)
            assert child.depth == node.depth + 1, "Child depth must equal parent depth + 1"
            
            # Pruning Check 1: Exceed boundaries (capacity / zero)
            if next_state < 0 or next_state > capacity:
                child.status = "PRUNED"
                pruned_nodes_count[0] += 1
                continue
                
            # Pruning Check 2: Cycle detection (state already in ancestor chain)
            if next_state in active_path_states:
                child.status = "PRUNED"
                pruned_nodes_count[0] += 1
                continue
                
            # Recursive step
            active_path_states.add(next_state)
            child.status = "VISITED"
            result = dls_visit(child)
            active_path_states.remove(next_state)
            
            if result is not None:
                return [node] + result
                
        return None

    # Run the search starting at root if not already at target
    if start_state == target_state:
        solution_path_nodes = [root_node]
    else:
        solution_path_nodes = dls_visit(root_node)
    
    target_found = target_node is not None
    solution_path = []
    
    if target_found:
        # Reconstruct path using parent relationships (Step 4)
        solution_path_nodes_reconstructed = []
        curr = target_node
        while curr is not None:
            solution_path_nodes_reconstructed.append(curr)
            if curr.parent_id is None:
                break
            curr = all_nodes[curr.parent_id]
        solution_path_nodes_reconstructed.reverse()
        
        solution_path = [n.state for n in solution_path_nodes_reconstructed]
        
        # Label path elements for visualization
        for n in all_nodes.values():
            if n.state == target_state and n.status == "TARGET":
                pass # keep TARGET status
            elif n in solution_path_nodes_reconstructed:
                n.status = "SOLUTION_PATH"
                
        termination_reason = "TARGET_FOUND"
        target_depth = len(solution_path) - 1
        
        # Debug validations (Step 10)
        assert solution_path[0] == start_state, "Final path must start with initial_state"
        assert solution_path[-1] == target_state, "Final path must end with target_state"
        if start_state == target_state:
            assert target_depth == 0, "Target depth must be 0 if initial_state == target_state"
            assert len(solution_path) == 1, "Path must contain only start_state when target equals start state"
        else:
            assert target_depth > 0, "Target depth must be greater than 0 if initial_state != target_state"
        for i in range(1, len(solution_path)):
            diff = solution_path[i] - solution_path[i-1]
            assert diff in [100, 200, -100, -200], f"Invalid transition action: {diff}"
            
    else:
        # Determine why it stopped
        reached_limit = any(n.depth >= depth_limit for n in all_nodes.values())
        if reached_limit:
            termination_reason = "DEPTH_LIMIT_REACHED"
        else:
            termination_reason = "STATE_SPACE_EXHAUSTED"
        target_depth = 0

    return {
        "target_found": target_found,
        "initial_state": start_state,
        "target_state": target_state,
        "path": solution_path,
        "visited_states": list(set(traversal_order)) if traversal_order else [start_state],
        "traversal_order": traversal_order if traversal_order else [start_state],
        "explored_nodes": explored_nodes_count[0] if start_state != target_state else 1,
        "generated_nodes": generated_nodes_count[0],
        "pruned_nodes": pruned_nodes_count[0],
        "depth_limit": depth_limit,
        "target_depth": target_depth,
        "termination_reason": termination_reason,
        "nodes": [n.to_dict() for n in all_nodes.values()]
    }
