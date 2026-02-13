#!/usr/bin/env python3
"""
Validation script for ELO rating calculator implementation.

This script tests the ELO calculator with sample F1 race data to ensure
the implementation is working correctly.
"""

import sys
import os
from datetime import date
from decimal import Decimal

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(__file__))

try:
    from ml.elo_calculator import ELOCalculator, ELORatingUpdate
    print("✅ Successfully imported ELO calculator")
except ImportError as e:
    print(f"❌ Failed to import ELO calculator: {e}")
    sys.exit(1)

# Mock RaceResult class for testing
class MockRaceResult:
    """Mock race result for testing."""

    def __init__(self, race_id, driver_id, team_id, final_position, status="finished"):
        self.race_id = race_id
        self.driver_id = driver_id
        self.team_id = team_id
        self.final_position = final_position
        self.status = status

    def __repr__(self):
        return f"MockRaceResult(driver_id={self.driver_id}, position={self.final_position})"

# Mock ResultStatus enum for testing
class MockResultStatus:
    FINISHED = "finished"
    DNF = "dnf"
    RETIRED = "retired"
    DISQUALIFIED = "disqualified"


def test_basic_calculations():
    """Test basic ELO calculations."""
    print("\n🧮 Testing basic ELO calculations...")

    calculator = ELOCalculator()

    # Test expected score calculation
    expected_score = calculator.calculate_expected_score(1500, 1500)
    assert abs(expected_score - 0.5) < 0.001, f"Expected 0.5, got {expected_score}"
    print("✅ Expected score calculation: PASS")

    # Test position scoring
    position_score = calculator.calculate_position_score(1, 20)
    assert position_score == 1.0, f"Winner should get 1.0, got {position_score}"

    position_score = calculator.calculate_position_score(20, 20)
    assert position_score == 0.0, f"Last place should get 0.0, got {position_score}"
    print("✅ Position scoring: PASS")

    # Test expected position
    ratings = [1600, 1500, 1400, 1300]
    expected_pos = calculator.calculate_expected_position(1600, ratings)
    assert expected_pos == 1.0, f"Highest rated should expect position 1, got {expected_pos}"
    print("✅ Expected position calculation: PASS")


def test_realistic_race_scenario():
    """Test with a realistic F1 race scenario."""
    print("\n🏁 Testing realistic F1 race scenario...")

    calculator = ELOCalculator()

    # Create mock race results (2024 Saudi Arabian GP style scenario)
    race_results = [
        MockRaceResult(100, 1, 1, 1, MockResultStatus.FINISHED),    # Max Verstappen - 1st
        MockRaceResult(100, 2, 1, 3, MockResultStatus.FINISHED),    # Sergio Perez - 3rd
        MockRaceResult(100, 3, 2, 2, MockResultStatus.FINISHED),    # Charles Leclerc - 2nd
        MockRaceResult(100, 4, 2, 4, MockResultStatus.FINISHED),    # Carlos Sainz - 4th
        MockRaceResult(100, 5, 3, 5, MockResultStatus.FINISHED),    # George Russell - 5th
        MockRaceResult(100, 6, 3, None, MockResultStatus.DNF),      # Lewis Hamilton - DNF
    ]

    # Starting ratings (based on 2024 performance)
    driver_ratings = {
        1: 1650,  # Max Verstappen (highest)
        2: 1580,  # Sergio Perez
        3: 1560,  # Charles Leclerc
        4: 1540,  # Carlos Sainz
        5: 1520,  # George Russell
        6: 1540,  # Lewis Hamilton
    }

    # Calculate driver rating updates
    driver_updates = calculator.update_driver_ratings(race_results, driver_ratings)

    print("Driver rating updates:")
    for driver_id, update in driver_updates.items():
        print(f"  Driver {driver_id}: {update.old_rating} → {update.new_rating} (change: {update.rating_change:+d})")

    # Validate results
    assert len(driver_updates) == 6, f"Expected 6 driver updates, got {len(driver_updates)}"

    # Max won when expected to win - should have small positive change
    max_change = driver_updates[1].rating_change
    assert 0 <= max_change <= 20, f"Max's change should be small positive, got {max_change}"

    # Leclerc finished 2nd when rated 3rd - should gain rating
    leclerc_change = driver_updates[3].rating_change
    assert leclerc_change > 0, f"Leclerc should gain rating, got {leclerc_change}"

    # Hamilton DNF should lose significant rating
    hamilton_change = driver_updates[6].rating_change
    assert hamilton_change < -15, f"Hamilton DNF should lose significant rating, got {hamilton_change}"

    print("✅ Driver rating updates: PASS")

    # Test team ratings
    team_ratings = {1: 1600, 2: 1550, 3: 1530}  # Red Bull, Ferrari, Mercedes
    team_updates = calculator.update_team_ratings(race_results, team_ratings)

    print("\nTeam rating updates:")
    for team_id, update in team_updates.items():
        print(f"  Team {team_id}: {update.old_rating} → {update.new_rating} (change: {update.rating_change:+d})")

    assert len(team_updates) == 3, f"Expected 3 team updates, got {len(team_updates)}"
    print("✅ Team rating updates: PASS")


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n⚠️  Testing edge cases...")

    calculator = ELOCalculator()

    # Test with empty results
    empty_updates = calculator.update_driver_ratings([], {})
    assert empty_updates == {}, "Empty results should return empty updates"
    print("✅ Empty results handling: PASS")

    # Test with new driver (not in current ratings)
    race_results = [
        MockRaceResult(100, 999, 100, 1, MockResultStatus.FINISHED)  # New driver wins
    ]

    updates = calculator.update_driver_ratings(race_results, {})
    assert 999 in updates, "Should handle new driver"
    assert updates[999].old_rating == calculator.base_rating, "New driver should start with base rating"
    print("✅ New driver handling: PASS")

    # Test rating floor
    very_low_rating = {1: 600}
    dnf_results = [
        MockRaceResult(100, 1, 100, None, MockResultStatus.DNF)
    ]

    updates = calculator.update_driver_ratings(dnf_results, very_low_rating)
    assert updates[1].new_rating >= 500, f"Rating should not go below floor, got {updates[1].new_rating}"
    print("✅ Rating floor enforcement: PASS")


def test_batch_processing():
    """Test batch processing of multiple races."""
    print("\n📊 Testing batch processing...")

    calculator = ELOCalculator()

    # Create results for 2 races
    race1_results = [
        MockRaceResult(100, 1, 100, 1, MockResultStatus.FINISHED),  # Driver 1 wins
        MockRaceResult(100, 2, 200, 2, MockResultStatus.FINISHED),  # Driver 2 second
        MockRaceResult(100, 3, 300, 3, MockResultStatus.FINISHED),  # Driver 3 third
    ]

    race2_results = [
        MockRaceResult(101, 1, 100, 3, MockResultStatus.FINISHED),  # Driver 1 third (worse)
        MockRaceResult(101, 2, 200, 1, MockResultStatus.FINISHED),  # Driver 2 wins (better)
        MockRaceResult(101, 3, 300, 2, MockResultStatus.FINISHED),  # Driver 3 second (better)
    ]

    initial_driver_ratings = {1: 1500, 2: 1500, 3: 1500}
    initial_team_ratings = {100: 1500, 200: 1500, 300: 1500}

    final_driver_ratings, final_team_ratings, all_updates = calculator.batch_update_ratings(
        [race1_results, race2_results],
        initial_driver_ratings,
        initial_team_ratings
    )

    assert len(all_updates) == 2, f"Should have updates for 2 races, got {len(all_updates)}"
    assert len(final_driver_ratings) == 3, f"Should have 3 final driver ratings, got {len(final_driver_ratings)}"
    assert len(final_team_ratings) == 3, f"Should have 3 final team ratings, got {len(final_team_ratings)}"

    print(f"Final driver ratings: {final_driver_ratings}")
    print(f"Final team ratings: {final_team_ratings}")
    print("✅ Batch processing: PASS")


def test_factory_function():
    """Test the factory function."""
    print("\n🏭 Testing factory function...")

    from ml.elo_calculator import get_elo_calculator

    calculator = get_elo_calculator()
    assert isinstance(calculator, ELOCalculator), "Factory should return ELOCalculator instance"
    assert calculator.k_factor == 32, "Default K-factor should be 32"

    custom_calculator = get_elo_calculator(k_factor=24)
    assert custom_calculator.k_factor == 24, "Custom K-factor should be used"

    print("✅ Factory function: PASS")


def main():
    """Run all validation tests."""
    print("🏎️  F1 ELO Rating Calculator Validation")
    print("=" * 50)

    try:
        test_basic_calculations()
        test_realistic_race_scenario()
        test_edge_cases()
        test_batch_processing()
        test_factory_function()

        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED! ELO implementation is working correctly.")
        print("\nKey validation results:")
        print("✅ Basic mathematical formulas are correct")
        print("✅ Realistic race scenarios produce expected results")
        print("✅ Edge cases are handled properly")
        print("✅ Batch processing works for multiple races")
        print("✅ Factory function creates valid calculators")
        print("\nThe ELO rating calculator is ready for production use!")

        return True

    except Exception as e:
        print(f"\n❌ VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)