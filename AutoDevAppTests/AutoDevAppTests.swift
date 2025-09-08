import XCTest
@testable import AutoDevApp

class AutoDevAppTests: XCTestCase {
    func testLoadPassages() {
        let passages = loadPassages()
        XCTAssertFalse(passages.isEmpty, "Passages should not be empty")
    }

    func testScoreCalculation() {
        let passage = Passage(title: "Test Passage", passage: "Test text", questions: [
            Question(id: "q1", text: "Question 1", choices: ["A", "B", "C", "D"], answerIndex: 1)
        ])
        let viewModel = PassageDetailViewModel(passage: passage)
        viewModel.selectedAnswers["q1"] = 1
        XCTAssertEqual(viewModel.calculateScore(), 1, "Score should be 1")
    }

    func testScoreWithUnansweredQuestions() {
        let passage = Passage(title: "Test Passage", passage: "Test text", questions: [
            Question(id: "q1", text: "Question 1", choices: ["A", "B", "C", "D"], answerIndex: 1)
        ])
        let viewModel = PassageDetailViewModel(passage: passage)
        XCTAssertEqual(viewModel.calculateScore(), 0, "Score should be 0 for unanswered questions")
    }
}

class PassageDetailViewModel {
    var passage: Passage
    var selectedAnswers: [String: Int] = [:]

    init(passage: Passage) {
        self.passage = passage
    }

    func calculateScore() -> Int {
        var correctCount = 0
        for question in passage.questions {
            if let selectedAnswer = selectedAnswers[question.id], selectedAnswer == question.answerIndex {
                correctCount += 1
            }
        }
        return correctCount
    }
}