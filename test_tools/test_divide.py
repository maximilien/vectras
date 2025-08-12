def test_divide():
    """Test the fixed divide function."""
    try:
        # Test normal division
        result1 = divide(355, 113)
        assert abs(result1 - 3.1415929203539825) < 0.0001, f"Expected pi approximation, got {result1}"
        print("✅ Test 1 passed: 355/113 gives pi approximation")
        
        # Test division by zero
        try:
            divide(10, 0)
            assert False, "Should have raised ValueError"
        except ValueError:
            print("✅ Test 2 passed: Division by zero raises ValueError")
        
        # Test other divisions
        result2 = divide(10, 2)
        assert result2 == 5.0, f"Expected 5.0, got {result2}"
        print("✅ Test 3 passed: 10/2 = 5.0")
        
        print("🎉 All tests passed!")
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_divide()