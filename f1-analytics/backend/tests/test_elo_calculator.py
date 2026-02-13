"""
Unit tests for ELO calculator.

Tests the core ELO rating calculation logic including expected scores,
rating updates, and edge cases.
"""

import pytest
import math
from unittest.mock import Mock

from app.models.f1_models import RaceResult, ResultStatus
from ml.elo_calculator import ELOCalculator, ELORatingUpdate


class TestELOCalculator:
    """Test suite for ELO calculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = ELOCalculator(k_factor=32, base_rating=1500)

    def test_initialization(self):
        """Test calculator initialization."""
        assert self.calculator.k_factor == 32
        assert self.calculator.base_rating == 1500

        # Test custom parameters
        custom_calc = ELOCalculator(k_factor=24, base_rating=1600)
        assert custom_calc.k_factor == 24
        assert custom_calc.base_rating == 1600

    def test_calculate_expected_score(self):
        """Test expected score calculation."""
        # Equal ratings should give 0.5 probability
        result = self.calculator.calculate_expected_score(1500, 1500)
        assert abs(result - 0.5) < 0.001

        # Higher rated player should have higher probability
        result = self.calculator.calculate_expected_score(1600, 1500)
        assert result > 0.5

        # Lower rated player should have lower probability
        result = self.calculator.calculate_expected_score(1400, 1500)
        assert result < 0.5

        # Test extreme differences
        result = self.calculator.calculate_expected_score(2000, 1000)
        assert result > 0.99

        result = self.calculator.calculate_expected_score(1000, 2000)
        assert result < 0.01

    def test_calculate_position_score(self):
        """Test position to score conversion."""
        # Winner should get score of 1.0
        assert self.calculator.calculate_position_score(1, 20) == 1.0

        # Last place should get score of 0.0
        assert self.calculator.calculate_position_score(20, 20) == 0.0

        # Middle position should get middle score
        result = self.calculator.calculate_position_score(10, 20)
        expected = (20 - 10) / (20 - 1)  # (total - position) / (total - 1)
        assert abs(result - expected) < 0.001

        # Edge cases
        assert self.calculator.calculate_position_score(1, 1) == 1.0  # Only participant
        assert self.calculator.calculate_position_score(None, 20) == 0.0  # None position
        assert self.calculator.calculate_position_score(0, 20) == 0.0  # Invalid position
        assert self.calculator.calculate_position_score(21, 20) == 0.0  # Position out of range

    def test_calculate_expected_position(self):
        """Test expected position calculation."""
        # Test with equal ratings - should expect middle position
        ratings = [1500, 1500, 1500, 1500]
        result = self.calculator.calculate_expected_position(1500, ratings)
        # With equal ratings, each driver has 50% chance against others
        # Expected position should be around 2.5
        assert 2.0 <= result <= 3.0

        # Test with highest rating - should expect position 1
        ratings = [1600, 1500, 1400, 1300]
        result = self.calculator.calculate_expected_position(1600, ratings)
        assert result == 1.0

        # Test with lowest rating - should expect last position
        ratings = [1600, 1500, 1400, 1300]
        result = self.calculator.calculate_expected_position(1300, ratings)
        assert result == 4.0

        # Test edge cases
        assert self.calculator.calculate_expected_position(1500, []) == 0.0
        assert self.calculator.calculate_expected_position(1500, [1600]) == 0.5

    def test_get_rating_change(self):
        """Test rating change calculation."""
        total_participants = 20

        # Better than expected (position 5, expected 10) should increase rating
        change = self.calculator.get_rating_change(
            actual_position=5,
            expected_position=10.0,
            total_participants=total_participants,
            result_status=ResultStatus.FINISHED
        )
        assert change > 0

        # Worse than expected (position 15, expected 10) should decrease rating
        change = self.calculator.get_rating_change(
            actual_position=15,
            expected_position=10.0,
            total_participants=total_participants,
            result_status=ResultStatus.FINISHED
        )
        assert change < 0

        # Exactly as expected should give minimal change
        change = self.calculator.get_rating_change(
            actual_position=10,
            expected_position=10.0,
            total_participants=total_participants,
            result_status=ResultStatus.FINISHED
        )
        assert abs(change) < 2  # Should be very small

        # DNF should always decrease rating significantly
        change_dnf = self.calculator.get_rating_change(
            actual_position=None,
            expected_position=5.0,
            total_participants=total_participants,
            result_status=ResultStatus.DNF
        )
        assert change_dnf < 0

        # Retired should also decrease rating
        change_retired = self.calculator.get_rating_change(
            actual_position=None,
            expected_position=5.0,
            total_participants=total_participants,
            result_status=ResultStatus.RETIRED
        )
        assert change_retired < 0

    def test_update_driver_ratings_simple(self):
        """Test driver rating updates with simple scenario."""
        # Create mock race results
        race_results = []
        for i, (driver_id, position) in enumerate([(1, 1), (2, 2), (3, 3)]):
            result = Mock(spec=RaceResult)
            result.race_id = 100
            result.driver_id = driver_id
            result.final_position = position
            result.status = ResultStatus.FINISHED
            result.team_id = driver_id  # Simple mapping for test
            race_results.append(result)

        # All drivers start with equal ratings
        current_ratings = {1: 1500, 2: 1500, 3: 1500}

        # Calculate updates
        updates = self.calculator.update_driver_ratings(race_results, current_ratings)

        # Winner should gain rating
        assert updates[1].rating_change > 0
        assert updates[1].new_rating > 1500

        # Last place should lose rating
        assert updates[3].rating_change < 0
        assert updates[3].new_rating < 1500

        # Middle position change depends on expectation
        # All should have valid updates
        assert all(isinstance(update, ELORatingUpdate) for update in updates.values())
        assert all(update.entity_type == "driver" for update in updates.values())

    def test_update_driver_ratings_with_dnf(self):
        """Test driver rating updates with DNF."""
        race_results = []
        for i, (driver_id, position, status) in enumerate([
            (1, 1, ResultStatus.FINISHED),
            (2, None, ResultStatus.DNF),
            (3, 2, ResultStatus.FINISHED)
        ]):
            result = Mock(spec=RaceResult)
            result.race_id = 100
            result.driver_id = driver_id
            result.final_position = position
            result.status = status
            result.team_id = driver_id
            race_results.append(result)

        current_ratings = {1: 1500, 2: 1500, 3: 1500}
        updates = self.calculator.update_driver_ratings(race_results, current_ratings)

        # DNF driver should lose significant rating
        assert updates[2].rating_change < 0
        assert updates[2].new_rating < updates[2].old_rating

        # Winner should gain rating
        assert updates[1].rating_change > 0

    def test_update_team_ratings(self):
        """Test team rating updates."""
        # Create race results with teams having multiple drivers
        race_results = []
        for driver_id, team_id, position in [
            (1, 100, 1),  # Team 100 driver 1 - 1st place
            (2, 100, 5),  # Team 100 driver 2 - 5th place
            (3, 200, 2),  # Team 200 driver 1 - 2nd place
            (4, 200, 3),  # Team 200 driver 2 - 3rd place
        ]:
            result = Mock(spec=RaceResult)
            result.race_id = 100
            result.driver_id = driver_id
            result.team_id = team_id
            result.final_position = position
            result.status = ResultStatus.FINISHED
            race_results.append(result)

        current_ratings = {100: 1500, 200: 1500}
        updates = self.calculator.update_team_ratings(race_results, current_ratings)

        # Team 100 has best driver in 1st, should rank higher than Team 200 (best in 2nd)
        assert updates[100].final_position < updates[200].final_position

        # All teams should have valid updates
        assert all(isinstance(update, ELORatingUpdate) for update in updates.values())
        assert all(update.entity_type == "team" for update in updates.values())

    def test_batch_update_ratings(self):
        """Test batch processing of multiple races."""
        # Create results for 2 races
        race1_results = []
        for driver_id, position in [(1, 1), (2, 2), (3, 3)]:
            result = Mock(spec=RaceResult)
            result.race_id = 100
            result.driver_id = driver_id
            result.final_position = position
            result.status = ResultStatus.FINISHED
            result.team_id = driver_id
            race1_results.append(result)

        race2_results = []
        for driver_id, position in [(1, 3), (2, 1), (3, 2)]:  # Different order
            result = Mock(spec=RaceResult)
            result.race_id = 101
            result.driver_id = driver_id
            result.final_position = position
            result.status = ResultStatus.FINISHED
            result.team_id = driver_id
            race2_results.append(result)

        initial_driver_ratings = {1: 1500, 2: 1500, 3: 1500}
        initial_team_ratings = {1: 1500, 2: 1500, 3: 1500}

        final_driver_ratings, final_team_ratings, all_updates = self.calculator.batch_update_ratings(
            [race1_results, race2_results],
            initial_driver_ratings,
            initial_team_ratings
        )

        # Should have processed 2 races
        assert len(all_updates) == 2

        # Final ratings should be different from initial
        assert final_driver_ratings != initial_driver_ratings

        # Ratings should be reasonable (above minimum)
        assert all(rating >= 500 for rating in final_driver_ratings.values())

    def test_rating_floor(self):
        """Test that ratings don't go below minimum floor."""
        # Create a scenario where a driver would lose massive rating
        race_results = []
        result = Mock(spec=RaceResult)
        result.race_id = 100
        result.driver_id = 1
        result.final_position = None  # DNF
        result.status = ResultStatus.DNF
        result.team_id = 1
        race_results.append(result)

        # Start with very low rating
        current_ratings = {1: 600}
        updates = self.calculator.update_driver_ratings(race_results, current_ratings)

        # Rating should not go below 500
        assert updates[1].new_rating >= 500

    def test_empty_race_results(self):
        """Test handling of empty race results."""
        updates = self.calculator.update_driver_ratings([], {})
        assert updates == {}

        updates = self.calculator.update_team_ratings([], {})
        assert updates == {}

    def test_new_driver_default_rating(self):
        """Test that new drivers get default base rating."""
        race_results = []
        result = Mock(spec=RaceResult)
        result.race_id = 100
        result.driver_id = 999  # New driver not in current_ratings
        result.final_position = 1
        result.status = ResultStatus.FINISHED
        result.team_id = 999
        race_results.append(result)

        # Don't include driver 999 in current ratings
        current_ratings = {}
        updates = self.calculator.update_driver_ratings(race_results, current_ratings)

        # Should use base rating for calculation
        assert updates[999].old_rating == self.calculator.base_rating

    def test_factory_function(self):
        """Test the factory function."""
        from ml.elo_calculator import get_elo_calculator

        calc = get_elo_calculator()
        assert isinstance(calc, ELOCalculator)
        assert calc.k_factor == 32

        calc_custom = get_elo_calculator(k_factor=24)
        assert calc_custom.k_factor == 24


class TestELORatingUpdate:
    """Test suite for ELORatingUpdate dataclass."""

    def test_rating_update_creation(self):
        """Test creating rating update objects."""
        update = ELORatingUpdate(
            entity_id=1,
            entity_type="driver",
            old_rating=1500,
            new_rating=1520,
            rating_change=20,
            race_id=100,
            final_position=1,
            expected_position=3.5
        )

        assert update.entity_id == 1
        assert update.entity_type == "driver"
        assert update.old_rating == 1500
        assert update.new_rating == 1520
        assert update.rating_change == 20
        assert update.race_id == 100
        assert update.final_position == 1
        assert update.expected_position == 3.5


# Integration-style test
class TestELOCalculatorIntegration:
    """Integration tests for ELO calculator with realistic scenarios."""

    def test_realistic_race_scenario(self):
        """Test a realistic F1 race scenario."""
        calculator = ELOCalculator()

        # Create realistic driver ratings (based on 2023 standings)
        driver_ratings = {
            1: 1650,  # Max Verstappen - highest rated
            2: 1580,  # Sergio Perez
            3: 1560,  # Fernando Alonso
            4: 1540,  # Lewis Hamilton
            5: 1520,  # George Russell
            6: 1500,  # Carlos Sainz
            7: 1480,  # Charles Leclerc
            8: 1460,  # Lando Norris
            9: 1440,  # Oscar Piastri
            10: 1420  # Lance Stroll
        }

        # Create race where Max (highest rated) doesn't win
        race_results = []
        positions = [3, 1, 2, 4, 5, 6, 7, 8, 9, 10]  # Perez wins, Alonso 2nd, Max 3rd

        for i, (driver_id, position) in enumerate(zip(driver_ratings.keys(), positions)):
            result = Mock(spec=RaceResult)
            result.race_id = 100
            result.driver_id = driver_id
            result.final_position = position
            result.status = ResultStatus.FINISHED
            result.team_id = (driver_id - 1) // 2 + 1  # 2 drivers per team
            race_results.append(result)

        # Calculate updates
        updates = calculator.update_driver_ratings(race_results, driver_ratings)

        # Max (driver 1) finished 3rd when expected to win - should lose rating
        assert updates[1].rating_change < 0

        # Perez (driver 2) won when expected 2nd - should gain rating
        assert updates[2].rating_change > 0

        # Alonso (driver 3) finished 2nd when expected 3rd - should gain rating
        assert updates[3].rating_change > 0

        # Verify all updates are reasonable
        for update in updates.values():
            assert -50 <= update.rating_change <= 50  # Reasonable range for single race
            assert update.new_rating >= 500  # Above minimum floor