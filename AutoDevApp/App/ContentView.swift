import SwiftUI

struct ContentView: View {
    var body: some View {
        NavigationView {
            List(passageData) { passage in
                NavigationLink(destination: PassageDetailView(passage: passage)) {
                    HStack {
                        Text(passage.title)
                        Spacer()
                        Text("Score: \(passage.lastScore)").foregroundColor(.gray)
                    }
                }
            }
            .navigationTitle("Reading Passages")
        }
    }
}

struct PassageDetailView: View {
    let passage: Passage
    @State private var selectedAnswers: [String: Int] = [:]
    @State private var score: Int?

    var body: some View {
        VStack {
            Text(passage.passage)
                .padding()
            ForEach(passage.questions) { question in
                VStack(alignment: .leading) {
                    Text(question.text)
                    Picker("Select an answer", selection: $selectedAnswers[question.id]) {
                        ForEach(0..<question.choices.count) { index in
                            Text(question.choices[index]).tag(index as Int?)
                        }
                    }
                    .pickerStyle(SegmentedPickerStyle())
                }
            }
            Button("Submit") {
                score = calculateScore()
            }
            if let score = score {
                Text("Score: \(score)")
            }
        }
        .padding()
    }

    private func calculateScore() -> Int {
        var correctCount = 0
        for question in passage.questions {
            if let selectedAnswer = selectedAnswers[question.id], selectedAnswer == question.answerIndex {
                correctCount += 1
            }
        }
        return correctCount
    }
}

struct Passage: Identifiable, Codable {
    let id = UUID()
    let title: String
    let passage: String
    let questions: [Question]
    var lastScore: Int = 0
}

struct Question: Identifiable, Codable {
    let id: String
    let text: String
    let choices: [String]
    let answerIndex: Int
}

let passageData: [Passage] = loadPassages()

func loadPassages() -> [Passage] {
    guard let url = Bundle.main.url(forResource: "passages", withExtension: "json") else { return [] }
    do {
        let data = try Data(contentsOf: url)
        let decoder = JSONDecoder()
        return try decoder.decode([Passage].self, from: data)
    } catch {
        print("Error loading passages: \(error)")
        return []
    }
}