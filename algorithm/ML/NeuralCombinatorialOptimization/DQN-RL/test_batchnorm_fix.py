"""
Quick test to verify BatchNorm fix
"""

import os
import sys
import torch

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from dqn_model import DQNAgent

def test_batchnorm_fix():
    """Test that single sample doesn't cause BatchNorm error"""
    print("Testing BatchNorm fix for DQN...")
    
    # Create agent
    state_dim = 9
    action_dim = 101
    hidden_dim = 512
    
    agent = DQNAgent(
        state_dim=state_dim,
        action_dim=action_dim,
        hidden_dim=hidden_dim,
        learning_rate=3e-4,
        gamma=0.98,
        epsilon_start=1.0,
        epsilon_end=0.01,
        epsilon_decay=0.997,
        buffer_size=50000,
        use_double_dqn=True,
        use_dueling=True,
        use_prioritized_replay=False
    )
    
    # Test with single state (this was causing the error)
    print("Testing single sample inference...")
    state = torch.randn(state_dim)  # Single state, no batch dimension
    valid_mask = torch.ones(action_dim, dtype=torch.bool)
    
    try:
        action = agent.select_action(state, valid_mask)
        print(f"✓ Single sample test passed! Action selected: {action}")
    except ValueError as e:
        print(f"✗ Single sample test failed! Error: {e}")
        return False
    
    # Test with batch (should also work)
    print("\nTesting batch inference...")
    states_batch = torch.randn(32, state_dim)  # Batch of 32
    
    try:
        agent.policy_net.eval()
        with torch.no_grad():
            q_values = agent.policy_net(states_batch)
        print(f"✓ Batch test passed! Output shape: {q_values.shape}")
    except Exception as e:
        print(f"✗ Batch test failed! Error: {e}")
        return False
    
    # Test training update (with batch)
    print("\nTesting training update...")
    
    # Add some experiences
    for _ in range(100):
        state = torch.randn(state_dim)
        action = torch.randint(0, action_dim, (1,)).item()
        reward = torch.randn(1).item()
        next_state = torch.randn(state_dim)
        done = False
        agent.memory.push(state, action, reward, next_state, done)
    
    try:
        loss = agent.update(batch_size=64)
        print(f"✓ Training update passed! Loss: {loss:.4f}")
    except Exception as e:
        print(f"✗ Training update failed! Error: {e}")
        return False
    
    print("\n" + "="*60)
    print("ALL TESTS PASSED! ✓")
    print("="*60)
    print("\nBatchNorm fix is working correctly!")
    print("You can now run: python train.py")
    
    return True

if __name__ == '__main__':
    test_batchnorm_fix()
